"""
bot/images.py
-------------
Descarga y valida imágenes adjuntas a un mensaje de Discord, para que
el bot pueda "verlas" al responder con IA (Claude soporta imágenes en
el mismo mensaje que el texto).

Reglas de seguridad:
- Solo se aceptan tipos de imagen conocidos (jpeg, png, gif, webp) --
  cualquier otro adjunto (video, audio, .exe, .zip, etc.) se ignora.
- Se aplica un límite de tamaño por imagen (MAX_IMAGE_SIZE_MB en el
  .env) para evitar picos de costo con archivos muy pesados.
- Se aplica un límite de cuántas imágenes se procesan por mensaje
  (MAX_IMAGES_PER_MESSAGE en el .env) por la misma razón.
- Nunca se ejecuta ni se abre el archivo -- solo se lee su contenido en
  memoria y se manda a la API de Claude como datos, igual que se
  mandaría el texto.
"""

import logging

import aiohttp
import discord

logger = logging.getLogger("staff")

# image/jpeg, image/png, image/gif, image/webp -- los únicos tipos que
# la API de Claude acepta como imagen.
_SUPPORTED_CONTENT_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}


def _is_supported_image(attachment: discord.Attachment) -> bool:
    content_type = (attachment.content_type or "").split(";")[0].strip().lower()
    return content_type in _SUPPORTED_CONTENT_TYPES


async def collect_images(
    message: discord.Message,
    *,
    max_images: int,
    max_size_mb: int,
) -> list[dict]:
    """
    Revisa los adjuntos del mensaje y devuelve una lista de bloques de
    imagen listos para mandar a la API de Claude (formato
    {"type": "image", "source": {...}}), respetando los límites de
    cantidad y tamaño. Los adjuntos que no son imágenes soportadas, o
    que superan el límite de tamaño, se ignoran (se loguea el motivo,
    no se detiene la respuesta del bot).
    """
    if not message.attachments:
        return []

    max_size_bytes = max_size_mb * 1024 * 1024
    images: list[dict] = []

    async with aiohttp.ClientSession() as session:
        for attachment in message.attachments:
            if len(images) >= max_images:
                logger.info(
                    "Se ignoró un adjunto de %s: ya se alcanzó el máximo de %d imágenes por mensaje.",
                    message.author, max_images,
                )
                break

            if not _is_supported_image(attachment):
                continue

            if attachment.size > max_size_bytes:
                logger.info(
                    "Se ignoró una imagen de %s por tamaño (%.1f MB > límite de %d MB).",
                    message.author, attachment.size / 1024 / 1024, max_size_mb,
                )
                continue

            try:
                async with session.get(attachment.url) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "No se pudo descargar un adjunto de %s (HTTP %d).",
                            message.author, resp.status,
                        )
                        continue
                    raw = await resp.read()
            except Exception as e:
                logger.warning("Error descargando un adjunto de %s: %s", message.author, e)
                continue

            if len(raw) > max_size_bytes:
                # El tamaño reportado por Discord y el real pueden diferir muy poco;
                # se vuelve a chequear el tamaño real descargado por seguridad.
                continue

            import base64
            content_type = (attachment.content_type or "").split(";")[0].strip().lower()
            images.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": _SUPPORTED_CONTENT_TYPES[content_type],
                    "data": base64.b64encode(raw).decode("ascii"),
                },
            })

    return images
