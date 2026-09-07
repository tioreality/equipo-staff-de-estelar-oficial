"""
bot/antispam.py
----------------
Controles anti-spam para las respuestas de IA del Jefe, con el mismo
criterio de seguridad que TAMAGO:
- Tiempo de espera (cooldown) entre respuestas, por usuario y canal.
- Limite global de respuestas por minuto (protege el costo de la API).
- Lista de canales autorizados -- por defecto NINGUNO: hay que poner al
  menos un canal en ALLOWED_CHANNEL_IDS (.env) antes de que el bot
  responda con IA en algun canal.
- Deteccion de mensajes repetidos (el mismo texto, seguido, del mismo
  usuario).
- Prevencion de bucles/spam entre bots: eso se resuelve en
  bot/client.py ignorando CUALQUIER mensaje enviado por un bot
  (incluido este mismo), antes de llegar hasta aqui.

En esta primera version (sin panel ni base de datos todavia), el
interruptor de IA y los canales autorizados viven en memoria/.env; en
TAMAGO esto mismo empezo igual y se movio a una base de datos editable
desde un panel web mas adelante -- se puede hacer lo mismo aqui cuando
haga falta.
"""

import time

_last_response_at: dict[tuple[int, int], float] = {}  # (channel_id, user_id) -> timestamp
_recent_global_responses: list[float] = []
_last_message_by_user: dict[int, str] = {}


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def check_message(
    *,
    channel_id: int,
    user_id: int,
    content: str,
    enabled: bool,
    allowed_channel_ids: frozenset[int],
    cooldown_seconds: int,
    max_responses_per_minute: int,
) -> str | None:
    """
    Decide si el bot deberia responder con IA a este mensaje.
    Devuelve None si puede responder, o un texto corto con el motivo del
    bloqueo (para loguear) si no deberia responder.
    """
    if not enabled:
        return "interruptor global de IA apagado"

    if channel_id not in allowed_channel_ids:
        return "canal no autorizado para respuestas de IA"

    now = time.monotonic()

    key = (channel_id, user_id)
    last = _last_response_at.get(key)
    if last is not None and (now - last) < cooldown_seconds:
        return "cooldown por usuario todavia activo"

    global _recent_global_responses
    _recent_global_responses = [t for t in _recent_global_responses if now - t <= 60]
    if len(_recent_global_responses) >= max_responses_per_minute:
        return "limite global de respuestas por minuto alcanzado"

    normalized = _normalize(content)
    if normalized and _last_message_by_user.get(user_id) == normalized:
        return "mensaje repetido"

    return None


def register_response(*, channel_id: int, user_id: int, content: str) -> None:
    """Se llama despues de responder, para que los limites de arriba surtan efecto."""
    now = time.monotonic()
    _last_response_at[(channel_id, user_id)] = now
    _recent_global_responses.append(now)
    _last_message_by_user[user_id] = _normalize(content)
