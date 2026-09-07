"""
shared/db.py
------------
Conexión a la base de datos MySQL compartida entre el panel y los 6
bots del equipo (Jefe, Zyren, Luna, Aurora, Aria, Teddy).

Todos los servicios se conectan a la MISMA base de datos, cada uno
leyendo las mismas variables de entorno (MYSQL_HOST, MYSQL_PORT,
MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE). Así, un cambio guardado
desde el panel lo puede leer cualquier bot en su siguiente respuesta,
sin reiniciar nada.

Mismo patrón que shared/db.py de TAMAGO, a propósito.

Ningún secreto vive en este archivo: todo viene de variables de
entorno.
"""

import os
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class DBConfigError(Exception):
    """Error de configuración de la base de datos: falta alguna variable obligatoria."""


def _build_database_url() -> str:
    host = os.getenv("MYSQL_HOST", "").strip()
    port = os.getenv("MYSQL_PORT", "3306").strip()
    user = os.getenv("MYSQL_USER", "").strip()
    password = os.getenv("MYSQL_PASSWORD", "").strip()
    database = os.getenv("MYSQL_DATABASE", "").strip()

    faltantes = [
        nombre
        for nombre, valor in [
            ("MYSQL_HOST", host),
            ("MYSQL_USER", user),
            ("MYSQL_PASSWORD", password),
            ("MYSQL_DATABASE", database),
        ]
        if not valor
    ]
    if faltantes:
        raise DBConfigError(
            "Faltan variables de entorno para conectar a la base de datos: "
            + ", ".join(faltantes)
            + ". Revisa tu archivo .env (o las Variables del servicio en Railway)."
        )

    # pymysql como driver; los valores se escapan automáticamente (nunca se
    # arma la URL con texto pegado a mano en otras partes del código).
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_build_database_url(), pool_pre_ping=True, pool_recycle=280)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


@contextmanager
def session_scope():
    """Uso: with session_scope() as session: ... (hace commit/rollback solo)."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Crea las tablas que todavía no existan. Seguro de correr varias veces."""
    Base.metadata.create_all(get_engine())


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------


class BotConfig(Base):
    """
    Configuración editable de UN bot del equipo (fila por bot: jefe,
    zyren, luna, aurora, aria, teddy). El panel escribe aquí; cada bot
    lee su propia fila (por bot_slug) antes de responder con IA.

    Si la base de datos no responde por algún motivo, cada bot cae de
    vuelta a la personalidad fija en su propio bot/personalidad.py
    (nunca se queda sin poder responder solo por un problema de DB).
    """

    __tablename__ = "bot_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_slug = Column(String(32), unique=True, nullable=False)  # jefe, zyren, luna, aurora, aria, teddy
    display_name = Column(String(100), nullable=False)  # ej: "Zyren (Programador)"

    personality_text = Column(Text, nullable=True)  # si es NULL, el bot usa su texto fijo de código
    tone = Column(String(255), nullable=True)
    language = Column(String(100), nullable=True)
    allowed_topics = Column(Text, nullable=True)
    forbidden_topics = Column(Text, nullable=True)

    ai_enabled = Column(Boolean, nullable=False, server_default="1")

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(100), nullable=True)  # username de Discord de quien hizo el último cambio


class BotEvent(Base):
    """
    Registro de actividad para la pantalla de "logs" del panel.
    Mismo propósito que en TAMAGO: complemento visual a los logs en
    archivo de cada bot, no un reemplazo.
    """

    __tablename__ = "bot_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    bot_slug = Column(String(32), nullable=True)
    event_type = Column(String(50), nullable=False)  # ej: "comando", "bloqueo", "error", "cambio_config"
    description = Column(Text, nullable=False)
    guild_id = Column(String(32), nullable=True)
    channel_id = Column(String(32), nullable=True)
    user_id = Column(String(32), nullable=True)
