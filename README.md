# Staff de Estelar Oficial

Bot base ("Jefe") de un futuro equipo de bots de Discord para apoyar a
Douglas (Estelar Oficial) en sus proyectos, empezando por la app
Android **StarOficial**.

Sigue el mismo patrón probado en el proyecto **TAMAGO** (bots de
Discord conversacionales con `discord.py` + la API de Claude), pero
está en su propio repositorio porque es un servidor de Discord y un
propósito distintos.

## Estado actual — Etapa 1 (MVP)

- ✅ Conexión a Discord, comando `!ping`.
- ✅ Responde con IA (personalidad de "Jefe") cuando lo mencionan en un
  canal autorizado.
- ✅ Anti-spam: cooldown, límite por minuto, canales autorizados,
  mensajes repetidos, interruptor `!jefe on/off/estado` (solo Admins).
- ⏳ Sin base de datos ni panel web todavía — la personalidad vive en
  `bot/personalidad.py` (código), y el interruptor de IA se reinicia
  al reiniciar el bot.
- ⏳ Los demás bots-empleado (Desarrollador, Diseñador, Marketing,
  Manager, UI) no existen todavía.
- ⏳ No hay ninguna conexión automática con Claude Code ni con el
  repositorio de StarOficial — el Jefe solo sabe lo que se le cuenta en
  la conversación de Discord.

## Instalar y ejecutar (Windows / PowerShell)

1. Instala Python desde https://python.org (marca "Add Python to PATH").
2. Instala las dependencias:
   ```powershell
   pip install -r requirements.txt
   ```
3. Copia `.env.example` como `.env` y rellena tus valores reales
   (token del bot, clave de Anthropic, etc.). **Nunca subas `.env` a
   git** — ya está en `.gitignore`.
4. Corre el bot:
   ```powershell
   python run.py
   ```
5. Detenlo con `Ctrl+C` en la misma terminal.

## Probarlo

- En el servidor de Discord donde agregaste el bot, escribe `!ping` —
  debe responder "Pong. Soy Staff de Estelar Oficial y estoy en
  línea...".
- Menciónalo directo (`@Staff de Estelar Oficial ¿cómo estás?`) en un
  canal que hayas puesto en `ALLOWED_CHANNEL_IDS` — debe responder con
  IA, con personalidad de Jefe.
- Si no responde a la mención, revisa que el canal esté en
  `ALLOWED_CHANNEL_IDS` y que la terminal no muestre ningún error.

## Próximos pasos posibles

1. Confirmar que StarOficial tiene su propio repositorio, para decidir
   cómo el Jefe podría reportar avances reales (por ahora, contárselo
   tú mismo en el chat es lo más simple y seguro).
2. Base de datos + panel web para editar la personalidad sin tocar
   código (igual que TAMAGO).
3. Crear los bots-empleado (Desarrollador, Diseñador, Marketing,
   Manager, UI) uno a la vez, cada uno con su propia app de Discord.
4. Definir si/cómo esos bots conversan entre ellos (con límites de
   turnos y frecuencia, igual que se planeó para TAMAGO).
