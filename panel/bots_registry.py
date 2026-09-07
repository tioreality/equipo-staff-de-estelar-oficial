"""
panel/bots_registry.py
-----------------------
Lista fija de los 6 bots del equipo Estelar Oficial (slug + nombre
para mostrar). Esto vive en código (no en base de datos) porque no
esperamos agregar/quitar bots todo el tiempo desde el panel -- cuando
se sume un bot nuevo, se agrega aquí y se corre init_db() una vez.

Sirve para:
- Saber qué filas debe tener la tabla bot_configs (y crearlas con
  valores por defecto la primera vez que el panel arranca).
- Mostrar los 6 bots en el dashboard aunque la fila en base de datos
  todavía no tenga personalidad personalizada guardada.
"""

BOTS = [
    {"slug": "jefe", "display_name": "Jefe (Staff de Estelar Oficial)"},
    {"slug": "zyren", "display_name": "Zyren (Programador)"},
    {"slug": "luna", "display_name": "Luna (Diseñadora)"},
    {"slug": "aurora", "display_name": "Aurora (Desarrolladora de UI)"},
    {"slug": "aria", "display_name": "Aria (Jefe de Marketing)"},
    {"slug": "teddy", "display_name": "Teddy (Manager)"},
]

BOT_SLUGS = {b["slug"] for b in BOTS}


def display_name_for(slug: str) -> str:
    for b in BOTS:
        if b["slug"] == slug:
            return b["display_name"]
    return slug
