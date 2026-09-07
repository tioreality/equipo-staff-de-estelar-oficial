"""
panel/main.py
-------------
Punto de entrada del panel web del equipo Estelar Oficial. Se ejecuta
como un servicio separado en Railway, y comparte la misma base de
datos MySQL (Hostinger) con los 6 bots (ver shared/db.py).

Qué hace esta versión:
- Login con Discord (sin contraseñas propias).
- Verificación de que quien entra tiene el rol de administrador en el
  servidor del equipo Estelar.
- Dashboard con los 6 bots: ver y editar personalidad/tono/temas, y
  encender/apagar sus respuestas de IA -- todo se guarda en la base de
  datos compartida, que cada bot lee antes de responder.

Cómo correrlo localmente:
    uvicorn panel.main:app --reload --port 8000
Y abrir http://localhost:8000 en el navegador.
"""

import logging
import secrets
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from starlette.middleware.sessions import SessionMiddleware

from .config import PanelConfigError, load_panel_config
from .auth import AuthError, build_authorize_url, exchange_code_for_user, user_is_admin
from .bots_registry import BOTS, BOT_SLUGS, display_name_for, short_name_for, color_for
from shared.db import DBConfigError, get_engine, init_db, session_scope, BotConfig, BotEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("estelar.panel")

templates = Jinja2Templates(directory="panel/templates")

app = FastAPI(title="Panel del Equipo Estelar Oficial")
app.mount("/static", StaticFiles(directory="panel/static"), name="static")

try:
    config = load_panel_config()
    app.add_middleware(SessionMiddleware, secret_key=config.session_secret)
except PanelConfigError as e:
    # No tumbamos el proceso de inmediato: mostramos el error en cada
    # página, para que quien lo despliegue vea exactamente qué falta en
    # vez de un stack trace confuso.
    config = None
    _config_error = str(e)
    app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))
else:
    _config_error = None


def _config_check(request: Request):
    if _config_error:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"mensaje": _config_error},
            status_code=500,
        )
    return None


def _require_login(request: Request):
    """Devuelve una respuesta de redirect si no hay sesión, o None si sí la hay."""
    if not request.session.get("user_id"):
        return RedirectResponse("/")
    return None


def _ensure_bot_rows():
    """
    Crea (si no existen) las filas de bot_configs para los 6 bots
    conocidos, con valores por defecto (sin personalidad personalizada
    -- el bot usa su texto fijo de código -- e IA activada). Seguro de
    llamar en cada carga del dashboard.
    """
    with session_scope() as session:
        existentes = {row.bot_slug for row in session.query(BotConfig.bot_slug).all()}
        for bot in BOTS:
            if bot["slug"] not in existentes:
                session.add(BotConfig(
                    bot_slug=bot["slug"],
                    display_name=bot["display_name"],
                    ai_enabled=True,
                ))


@app.on_event("startup")
async def on_startup():
    if config is None:
        return
    try:
        init_db()
        _ensure_bot_rows()
        logger.info("Base de datos lista: tablas creadas y filas de bots aseguradas.")
    except Exception as e:
        # No tumbamos el panel si la DB no responde al arrancar -- cada
        # ruta que la necesite mostrará su propio error claro.
        logger.error("No se pudo preparar la base de datos al iniciar: %s", e)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    error = _config_check(request)
    if error:
        return error

    if request.session.get("user_id"):
        return RedirectResponse("/dashboard")

    return templates.TemplateResponse(request, "login.html")


@app.get("/login")
async def login(request: Request):
    error = _config_check(request)
    if error:
        return error

    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    return RedirectResponse(build_authorize_url(config, state))


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    err = _config_check(request)
    if err:
        return err

    if error:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"mensaje": "Inicio de sesión cancelado en Discord."},
            status_code=400,
        )

    if not code or state != request.session.get("oauth_state"):
        return templates.TemplateResponse(
            request,
            "error.html",
            {"mensaje": "La solicitud de login no es válida. Intenta de nuevo desde /login."},
            status_code=400,
        )

    try:
        discord_user = await exchange_code_for_user(config, code)
        es_admin = await user_is_admin(config, discord_user["id"])
    except AuthError as e:
        return templates.TemplateResponse(
            request, "error.html", {"mensaje": str(e)}, status_code=502
        )

    if not es_admin:
        logger.info("Acceso denegado al panel para usuario de Discord %s", discord_user.get("id"))
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "mensaje": "Tu cuenta de Discord no tiene el rol de administrador en el servidor del equipo Estelar, así que no puedes entrar al panel.",
            },
            status_code=403,
        )

    request.session["user_id"] = discord_user["id"]
    request.session["username"] = discord_user.get("username", "Admin")
    request.session["avatar_url"] = _discord_avatar_url(discord_user)
    logger.info("Login exitoso en el panel: %s (%s)", discord_user.get("username"), discord_user["id"])
    return RedirectResponse("/dashboard")


def _discord_avatar_url(discord_user: dict) -> str:
    """
    Arma la URL pública de la foto de perfil de Discord del usuario.
    Si no tiene avatar propio (cuenta nueva o sin foto), cae al avatar
    por defecto que asigna Discord según su discriminador/ID -- nunca
    queda una imagen rota.
    """
    user_id = discord_user.get("id", "")
    avatar_hash = discord_user.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=64"

    # Avatar por defecto: para cuentas nuevas (sistema de username sin
    # discriminador) Discord usa (id >> 22) % 6; mantenemos un cálculo
    # simple y seguro que nunca lanza excepción.
    try:
        default_index = (int(user_id) >> 22) % 6
    except (TypeError, ValueError):
        default_index = 0
    return f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    error = _config_check(request)
    if error:
        return error
    redirect = _require_login(request)
    if redirect:
        return redirect

    db_status = "conectada"
    bots = []
    events_by_day = []
    total_events = 0
    events_7d = 0
    try:
        with get_engine().connect():
            pass
        _ensure_bot_rows()
        with session_scope() as session:
            # Actividad total por bot (para las tarjetas, la leyenda de la
            # dona y el gráfico de barras) -- todo calculado a partir de
            # bot_events, ningún dato de ejemplo.
            eventos_por_bot = dict(
                session.query(BotEvent.bot_slug, func.count(BotEvent.id))
                .group_by(BotEvent.bot_slug)
                .all()
            )
            total_events = session.query(func.count(BotEvent.id)).scalar() or 0

            desde_7d = datetime.utcnow() - timedelta(days=7)
            events_7d = (
                session.query(func.count(BotEvent.id))
                .filter(BotEvent.created_at >= desde_7d)
                .scalar()
            ) or 0

            # Serie diaria de los últimos 14 días para el gráfico de línea.
            desde_14d = datetime.utcnow() - timedelta(days=13)
            conteo_diario = dict(
                session.query(func.date(BotEvent.created_at), func.count(BotEvent.id))
                .filter(BotEvent.created_at >= desde_14d)
                .group_by(func.date(BotEvent.created_at))
                .all()
            )
            for i in range(13, -1, -1):
                dia = (datetime.utcnow() - timedelta(days=i)).date()
                events_by_day.append({
                    "fecha": dia.strftime("%d/%m"),
                    "cantidad": conteo_diario.get(dia, 0),
                })

            rows = session.query(BotConfig).order_by(BotConfig.id).all()
            for row in rows:
                cantidad_bot = eventos_por_bot.get(row.bot_slug, 0)
                bots.append({
                    "slug": row.bot_slug,
                    "display_name": row.display_name or display_name_for(row.bot_slug),
                    "short_name": short_name_for(row.bot_slug),
                    "color": color_for(row.bot_slug),
                    "ai_enabled": row.ai_enabled,
                    "has_custom_personality": bool(row.personality_text),
                    "updated_at": row.updated_at,
                    "updated_by": row.updated_by,
                    "events": cantidad_bot,
                    "event_pct": round(cantidad_bot / total_events * 100) if total_events else 0,
                })
    except DBConfigError as e:
        db_status = f"no configurada ({e})"
    except Exception as e:  # conexión rechazada, credenciales inválidas, etc.
        db_status = f"error de conexión ({e})"

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "username": request.session.get("username"),
            "avatar_url": request.session.get("avatar_url"),
            "db_status": db_status,
            "bots": bots,
            "events_by_day": events_by_day,
            "total_events": total_events,
            "events_7d": events_7d,
        },
    )


@app.get("/logs", response_class=HTMLResponse)
async def logs(request: Request):
    error = _config_check(request)
    if error:
        return error
    redirect = _require_login(request)
    if redirect:
        return redirect

    db_status = "conectada"
    events = []
    try:
        with get_engine().connect():
            pass
        with session_scope() as session:
            rows = (
                session.query(BotEvent)
                .order_by(BotEvent.created_at.desc())
                .limit(100)
                .all()
            )
            for row in rows:
                events.append({
                    "created_at": row.created_at,
                    "bot_slug": row.bot_slug,
                    "bot_display_name": display_name_for(row.bot_slug) if row.bot_slug else None,
                    "event_type": row.event_type,
                    "description": row.description,
                })
    except DBConfigError as e:
        db_status = f"no configurada ({e})"
    except Exception as e:
        db_status = f"error de conexión ({e})"

    return templates.TemplateResponse(
        request,
        "logs.html",
        {
            "username": request.session.get("username"),
            "avatar_url": request.session.get("avatar_url"),
            "db_status": db_status,
            "events": events,
        },
    )


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    error = _config_check(request)
    if error:
        return error
    redirect = _require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request,
        "config.html",
        {
            "username": request.session.get("username"),
            "avatar_url": request.session.get("avatar_url"),
        },
    )


@app.get("/bots/{bot_slug}", response_class=HTMLResponse)
async def edit_bot(request: Request, bot_slug: str):
    error = _config_check(request)
    if error:
        return error
    redirect = _require_login(request)
    if redirect:
        return redirect

    if bot_slug not in BOT_SLUGS:
        return templates.TemplateResponse(
            request, "error.html", {"mensaje": f"No existe ningún bot con el identificador '{bot_slug}'."},
            status_code=404,
        )

    try:
        _ensure_bot_rows()
        with session_scope() as session:
            row = session.query(BotConfig).filter_by(bot_slug=bot_slug).one()
            bot = {
                "slug": row.bot_slug,
                "display_name": row.display_name or display_name_for(bot_slug),
                "personality_text": row.personality_text or "",
                "tone": row.tone or "",
                "language": row.language or "",
                "allowed_topics": row.allowed_topics or "",
                "forbidden_topics": row.forbidden_topics or "",
                "ai_enabled": row.ai_enabled,
                "updated_at": row.updated_at,
                "updated_by": row.updated_by,
            }
    except Exception as e:
        return templates.TemplateResponse(
            request, "error.html", {"mensaje": f"No se pudo leer la configuración de este bot: {e}"},
            status_code=500,
        )

    return templates.TemplateResponse(
        request,
        "edit_bot.html",
        {
            "bot": bot,
            "saved": False,
            "username": request.session.get("username"),
            "avatar_url": request.session.get("avatar_url"),
        },
    )


@app.post("/bots/{bot_slug}", response_class=HTMLResponse)
async def save_bot(
    request: Request,
    bot_slug: str,
    personality_text: str = Form(""),
    tone: str = Form(""),
    language: str = Form(""),
    allowed_topics: str = Form(""),
    forbidden_topics: str = Form(""),
    ai_enabled: str = Form(""),
):
    error = _config_check(request)
    if error:
        return error
    redirect = _require_login(request)
    if redirect:
        return redirect

    if bot_slug not in BOT_SLUGS:
        return templates.TemplateResponse(
            request, "error.html", {"mensaje": f"No existe ningún bot con el identificador '{bot_slug}'."},
            status_code=404,
        )

    username = request.session.get("username", "desconocido")
    ai_on = ai_enabled == "on"

    try:
        with session_scope() as session:
            row = session.query(BotConfig).filter_by(bot_slug=bot_slug).one()
            row.personality_text = personality_text.strip() or None
            row.tone = tone.strip() or None
            row.language = language.strip() or None
            row.allowed_topics = allowed_topics.strip() or None
            row.forbidden_topics = forbidden_topics.strip() or None
            row.ai_enabled = ai_on
            row.updated_by = username

            session.add(BotEvent(
                bot_slug=bot_slug,
                event_type="cambio_config",
                description=f"{username} actualizó la configuración de {bot_slug} desde el panel.",
            ))

        bot = {
            "slug": bot_slug,
            "display_name": display_name_for(bot_slug),
            "personality_text": personality_text,
            "tone": tone,
            "language": language,
            "allowed_topics": allowed_topics,
            "forbidden_topics": forbidden_topics,
            "ai_enabled": ai_on,
        }
    except Exception as e:
        return templates.TemplateResponse(
            request, "error.html", {"mensaje": f"No se pudo guardar la configuración: {e}"},
            status_code=500,
        )

    return templates.TemplateResponse(
        request,
        "edit_bot.html",
        {
            "bot": bot,
            "saved": True,
            "username": request.session.get("username"),
            "avatar_url": request.session.get("avatar_url"),
        },
    )


@app.post("/bots/{bot_slug}/toggle-ai")
async def toggle_ai(request: Request, bot_slug: str):
    """Enciende/apaga la IA de un bot directo desde el dashboard, sin abrir su página de edición."""
    error = _config_check(request)
    if error:
        return error
    redirect = _require_login(request)
    if redirect:
        return redirect

    if bot_slug not in BOT_SLUGS:
        return RedirectResponse("/dashboard", status_code=303)

    username = request.session.get("username", "desconocido")
    try:
        with session_scope() as session:
            row = session.query(BotConfig).filter_by(bot_slug=bot_slug).one()
            row.ai_enabled = not row.ai_enabled
            row.updated_by = username
            session.add(BotEvent(
                bot_slug=bot_slug,
                event_type="cambio_config",
                description=f"{username} {'activó' if row.ai_enabled else 'desactivó'} la IA de {bot_slug} desde el panel.",
            ))
    except Exception as e:
        logger.error("Error al alternar IA de %s: %s", bot_slug, e)

    return RedirectResponse("/dashboard", status_code=303)


@app.get("/health")
async def health():
    """Endpoint simple para que Railway confirme que el servicio está vivo."""
    return {"status": "ok"}
