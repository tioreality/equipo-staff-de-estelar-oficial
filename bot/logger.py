"""
bot/logger.py
-------------
Configura el sistema de registros (logs) del bot.

Que se guarda: eventos tecnicos (inicio, conexion, comandos ejecutados,
errores) con fecha y hora. NO se guardan tokens, claves ni contenido
privado de mensajes.

Donde se guarda: en la carpeta logs/, en un archivo que rota
automaticamente para no crecer sin limite.

Como borrarlo: puedes borrar el contenido de la carpeta logs/ en
cualquier momento con el bot detenido; se volvera a crear solo.
"""

import logging
import logging.handlers
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "staff.log")


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("staff")
    logger.setLevel(log_level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logging.getLogger("discord").setLevel(logging.WARNING)

    return logger
