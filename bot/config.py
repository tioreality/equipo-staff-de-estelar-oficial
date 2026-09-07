"""
bot/config.py
-------------
Carga y valida la configuracion del bot a partir de variables de entorno
(archivo .env). Ningun secreto se escribe aqui en el codigo: todo viene
del archivo .env, que nunca se sube al repositorio.

Si falta una variable obligatoria, el programa se detiene con un mensaje
claro en lugar de fallar de forma confusa mas adelante.

Nota para quien conozca el proyecto TAMAGO: este archivo es casi
identico al de TAMAGO a proposito -- es el mismo patron probado, para
que en el futuro sea facil mover este bot a la misma base de datos y
panel compartido si se decide unificarlos.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    """Error de configuracion: falta una variable obligatoria o tiene un valor invalido."""


@dataclass(frozen=True)
class Config:
    discord_token: str
    command_prefix: str
    guild_id: int | None
    log_level: str

    # Identifica a este bot (por ahora solo existe "jefe", pero se deja
    # preparado para cuando se sumen los bots-empleados: developer,
    # disenador, marketing, manager, ui).
    bot_slug: str

    anthropic_api_key: str
    anthropic_model: str

    ai_cooldown_seconds: int
    ai_max_responses_per_minute: int

    # Canales donde el bot puede responder con IA. En esta primera
    # version vive en el .env (no hay panel todavia); mas adelante,
    # igual que en TAMAGO, esto se puede mover a una base de datos
    # editable desde un panel web.
    allowed_channel_ids: frozenset[int]


def _get_optional_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(
            f"La variable {name} debe ser un numero entero (ID de Discord). "
            f"Valor recibido: {raw!r}"
        )


def _get_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        valor = int(raw)
    except ValueError:
        raise ConfigError(f"La variable {name} debe ser un numero entero. Valor recibido: {raw!r}")
    if valor <= 0:
        raise ConfigError(f"La variable {name} debe ser mayor que 0. Valor recibido: {raw!r}")
    return valor


def _parse_channel_ids(raw: str) -> frozenset[int]:
    ids = set()
    for pedazo in raw.replace(",", "\n").splitlines():
        pedazo = pedazo.strip()
        if pedazo.isdigit():
            ids.add(int(pedazo))
    return frozenset(ids)


def load_config() -> Config:
    """Lee y valida las variables de entorno. Lanza ConfigError si algo falta o es invalido."""

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "tu_token_aqui":
        raise ConfigError(
            "Falta DISCORD_TOKEN en el archivo .env (o sigue con el valor de ejemplo). "
            "Copia .env.example como .env y pega el token real del bot "
            "(Discord Developer Portal > Staff de Estelar Oficial > Bot > Reset Token)."
        )

    prefix = os.getenv("COMMAND_PREFIX", "!").strip() or "!"
    guild_id = _get_optional_int("GUILD_ID")

    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
    if log_level not in valid_levels:
        raise ConfigError(
            f"LOG_LEVEL={log_level!r} no es valido. Usa uno de: {', '.join(sorted(valid_levels))}."
        )

    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_api_key or anthropic_api_key == "tu_api_key_aqui":
        raise ConfigError(
            "Falta ANTHROPIC_API_KEY en el archivo .env. Puedes usar la misma clave "
            "que ya usa TAMAGO. Consiguela en: https://console.anthropic.com/settings/keys"
        )

    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929").strip()

    ai_cooldown_seconds = _get_positive_int("AI_COOLDOWN_SECONDS", 8)
    ai_max_responses_per_minute = _get_positive_int("AI_MAX_RESPONSES_PER_MINUTE", 10)

    bot_slug = os.getenv("BOT_SLUG", "jefe").strip() or "jefe"

    allowed_channel_ids = _parse_channel_ids(os.getenv("ALLOWED_CHANNEL_IDS", ""))

    return Config(
        discord_token=token,
        command_prefix=prefix,
        guild_id=guild_id,
        log_level=log_level,
        bot_slug=bot_slug,
        anthropic_api_key=anthropic_api_key,
        anthropic_model=anthropic_model,
        ai_cooldown_seconds=ai_cooldown_seconds,
        ai_max_responses_per_minute=ai_max_responses_per_minute,
        allowed_channel_ids=allowed_channel_ids,
    )
