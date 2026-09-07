"""
client.py
---------
Define la clase del bot "Jefe" (Staff de Estelar Oficial).

Etapa 1 (MVP): conexion con Discord, comando "!ping" de prueba, y
respuestas con IA cuando lo mencionan directamente (@Staff de Estelar
Oficial) en un canal autorizado, con la personalidad de "Jefe" fija en
codigo (bot/personalidad.py) y controles anti-spam (bot/antispam.py).

Mismo patron que bot/client.py de TAMAGO, simplificado porque todavia
no hay base de datos ni panel: el interruptor de IA es en memoria
("!jefe on/off") y los canales autorizados vienen del .env
(ALLOWED_CHANNEL_IDS).

Todavia NO incluye (llegara mas adelante, siguiendo el mismo plan por
etapas que uso TAMAGO):
- Personalidad editable desde un panel web (requiere base de datos).
- Los demas bots-empleado (Desarrollador, Disenador, Marketing,
  Manager, UI) y conversaciones entre bots.
- Cualquier integracion automatica con Claude Code / el proyecto
  StarOficial -- por ahora el Jefe solo sabe lo que Douglas le cuenta
  en la conversacion.
"""

import asyncio
import logging

import discord
from discord.ext import commands

from . import antispam
from .ai import generate_response
from .config import Config
from .images import collect_images
from .personalidad import get_active_personality

# Interruptor de IA en memoria (sin base de datos todavia): se reinicia
# a "activado" cada vez que el proceso arranca. Igual que TAMAGO en su
# primera version, antes de que este valor se moviera a una base de
# datos compartida con el panel web.
_ai_enabled = True


def _set_ai_enabled(value: bool) -> None:
    global _ai_enabled
    _ai_enabled = value


def _get_ai_enabled() -> bool:
    return _ai_enabled


async def _handle_ai_mention(bot: commands.Bot, config: Config, message: discord.Message) -> None:
    logger = logging.getLogger("staff")

    content = message.content
    for mention in (f"<@{bot.user.id}>", f"<@!{bot.user.id}>"):
        content = content.replace(mention, "")
    content = content.strip()

    images = await collect_images(
        message,
        max_images=config.max_images_per_message,
        max_size_mb=config.max_image_size_mb,
    )

    if not content:
        content = (
            "(la persona te mandó una o más imágenes sin escribir nada más -- coméntalas)"
            if images
            else "(la persona solo te mencionó, sin escribir nada más -- salúdala)"
        )

    if len(content) > 800:
        await message.channel.send(
            f"Ese mensaje es bastante largo, {message.author.mention} -- ¿me lo resumes un poco?"
        )
        return

    reason = antispam.check_message(
        channel_id=message.channel.id,
        user_id=message.author.id,
        content=content,
        enabled=_get_ai_enabled(),
        allowed_channel_ids=config.allowed_channel_ids,
        cooldown_seconds=config.ai_cooldown_seconds,
        max_responses_per_minute=config.ai_max_responses_per_minute,
    )
    if reason is not None:
        logger.info(
            "Respuesta de IA bloqueada (%s) -- canal=%s usuario=%s",
            reason, message.channel.id, message.author.id,
        )
        return

    personality = get_active_personality(config.bot_slug)

    async with message.channel.typing():
        try:
            reply = await generate_response(config, personality, content, images=images)
        except Exception as e:
            logger.error("Error llamando a la API de Claude: %s", e)
            await message.channel.send(
                f"Se me trabó algo un segundo, {message.author.mention} -- pregúntame de nuevo en un momento."
            )
            return

    antispam.register_response(channel_id=message.channel.id, user_id=message.author.id, content=content)
    logger.info("%s respondió con IA a %s en #%s", bot.user.name, message.author, message.channel)
    await message.channel.send(reply)


def build_bot(config: Config) -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=config.command_prefix, intents=intents)
    logger = logging.getLogger("staff")

    @bot.event
    async def on_ready():
        logger.info("Conectado como %s (ID: %s)", bot.user, bot.user.id)
        logger.info("Prefijo de comandos activo: %s", config.command_prefix)
        if not config.allowed_channel_ids:
            logger.warning(
                "ALLOWED_CHANNEL_IDS está vacío en el .env -- el bot no responderá con IA "
                "en ningún canal hasta que agregues al menos un ID."
            )
        if config.guild_id:
            guild = bot.get_guild(config.guild_id)
            if guild:
                logger.info("Servidor objetivo encontrado: %s", guild.name)
            else:
                logger.warning(
                    "GUILD_ID configurado (%s) pero el bot no está en ese servidor.",
                    config.guild_id,
                )

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Ese comando es solo para Administradores del servidor.")
            return
        logger.error("Error ejecutando un comando: %s", error)
        await ctx.send("Ocurrió un error al procesar ese comando. Ya quedó registrado.")

    @bot.event
    async def on_message(message: discord.Message):
        # Nunca respondemos a otros bots (ni a nosotros mismos): evita
        # bucles y respuestas en cadena cuando se sumen los demás bots.
        if message.author.bot:
            return

        ctx = await bot.get_context(message)
        if ctx.valid:
            await bot.invoke(ctx)
            return

        if bot.user in message.mentions:
            await _handle_ai_mention(bot, config, message)

    @bot.command(name="ping")
    async def ping(ctx: commands.Context):
        """Comando de prueba: confirma que el bot está vivo y respondiendo."""
        logger.info("Comando !ping usado por %s en #%s", ctx.author, ctx.channel)
        await ctx.send(f"Pong. Soy {bot.user.name} y estoy en línea, {ctx.author.mention}.")

    @bot.command(name="jefe")
    @commands.has_permissions(administrator=True)
    async def jefe_toggle(ctx: commands.Context, accion: str = "estado"):
        """Enciende/apaga/consulta las respuestas de IA. Solo Administradores.

        Nota: en esta primera version el valor vive en memoria (se
        reinicia si el bot se reinicia). Cuando se agregue un panel
        web, esto se movera a base de datos, igual que en TAMAGO.
        """
        accion = accion.lower().strip()
        if accion in ("on", "encender", "activar"):
            _set_ai_enabled(True)
            logger.info("IA activada por %s", ctx.author)
            await ctx.send("Listo, ya puedo responder con IA de nuevo.")
        elif accion in ("off", "apagar", "desactivar"):
            _set_ai_enabled(False)
            logger.info("IA desactivada por %s", ctx.author)
            await ctx.send("Ok, dejo de responder con IA hasta que me vuelvan a encender.")
        elif accion in ("estado", "status"):
            estado = "activada" if _get_ai_enabled() else "desactivada"
            await ctx.send(f"Mi IA está {estado} ahora mismo.")
        else:
            await ctx.send("Uso: `!jefe on`, `!jefe off` o `!jefe estado`.")

    return bot
