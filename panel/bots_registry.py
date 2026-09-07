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

# Un color fijo por bot, usado en el dashboard (tarjetas, leyenda del
# gráfico de dona, barras de actividad) para que cada bot se reconozca
# siempre por el mismo color en todo el panel.
BOT_COLORS = {
    "jefe": "#6366f1",    # índigo — coordinación
    "zyren": "#06b6d4",   # cian — desarrollo
    "luna": "#ec4899",    # rosa — diseño
    "aurora": "#8b5cf6",  # violeta — UI
    "aria": "#f97316",    # naranja — marketing
    "teddy": "#10b981",   # verde — gestión
}


def display_name_for(slug: str) -> str:
    for b in BOTS:
        if b["slug"] == slug:
            return b["display_name"]
    return slug


def short_name_for(slug: str) -> str:
    """Nombre corto del bot (sin el rol entre paréntesis), para tarjetas y gráficos."""
    return display_name_for(slug).split("(")[0].strip()


def color_for(slug: str) -> str:
    """Color fijo del bot para el dashboard; gris neutro si el slug no está en la lista."""
    return BOT_COLORS.get(slug, "#94a3b8")
