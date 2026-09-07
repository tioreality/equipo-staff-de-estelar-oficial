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
- ✅ Puede "ver" imágenes: si le mandas una imagen adjunta junto con la
  mención, la analiza y comenta con IA (límite de tamaño y de cantidad
  configurables en `.env` — `MAX_IMAGE_SIZE_MB`, `MAX_IMAGES_PER_MESSAGE`).
- ✅ Panel web (`panel/`) para editar personalidad y encender/apagar la
  IA de cada bot del equipo desde el navegador, con login por Discord
  (OAuth2 + rol de Administrador). Vive en este mismo repositorio pero
  se despliega como un **servicio aparte** en Railway (ver más abajo).
  Usa una base de datos MySQL compartida (Hostinger) — si la base no
  responde, cada bot sigue funcionando con la personalidad fija de su
  propio código.
- ⏳ Los demás bots-empleado (Zyren, Luna, Aurora, Aria, Teddy) ya
  existen en sus propios repositorios, pero todavía no leen su
  configuración desde la base de datos del panel (leen solo su código
  fijo) — ese es el siguiente paso.
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

## El panel web (`panel/`)

Vive en este mismo repositorio, pero es un **servicio distinto** al
bot — no corren como el mismo proceso. En Railway, dentro del mismo
proyecto, hay que tener **dos servicios apuntando a este repositorio**:

- Servicio del bot (el que ya existe): usa el proceso `worker` del
  `Procfile` (`python run.py`). Sin dominio público — un bot de
  Discord no necesita uno.
- Servicio del panel (nuevo): usa el proceso `panel` del `Procfile`
  (`uvicorn panel.main:app --host 0.0.0.0 --port $PORT`). Sí necesita
  dominio público (Settings → Networking → Generate Domain, puerto
  8080 o el que Railway detecte).

Para decirle a Railway qué proceso usar en cada servicio: al crear el
segundo servicio desde este mismo repo, en **Settings → Deploy → Custom
Start Command** pon exactamente:
```
uvicorn panel.main:app --host 0.0.0.0 --port $PORT
```

### Variables de entorno del panel (servicio "panel", no el del bot)

Ver `.env.example` para la lista completa con explicación de cada una.
En resumen: `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` (la base de datos
de Hostinger, compartida con los bots), `DISCORD_CLIENT_ID`,
`DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI` (debe coincidir
exactamente con un "Redirect" registrado en el Developer Portal),
`DISCORD_TOKEN` (el mismo token del bot Jefe, se usa solo para
verificar roles), `GUILD_ID`, `ADMIN_ROLE_ID`, y `PANEL_SECRET_KEY`
(una clave aleatoria larga, solo para firmar las cookies de sesión).

### Probar el panel

1. Abre la URL pública del servicio "panel" en Railway.
2. Clic en "Iniciar sesión con Discord" → inicia sesión con tu cuenta.
3. Si tu cuenta tiene el rol de Administrador configurado
   (`ADMIN_ROLE_ID`) en el servidor (`GUILD_ID`), entras al dashboard
   con los 6 bots listados.
4. Si no tiene el rol, verás un mensaje claro de acceso denegado (no
   un error técnico).
5. En el dashboard puedes: encender/apagar la IA de cada bot con un
   clic, o entrar a "Editar" para cambiar su personalidad, tono e
   idioma — se guarda en la base de datos compartida.

## Próximos pasos posibles

1. Confirmar que StarOficial tiene su propio repositorio, para decidir
   cómo el Jefe podría reportar avances reales (por ahora, contárselo
   tú mismo en el chat es lo más simple y seguro).
2. Modificar los 6 bots (Jefe, Zyren, Luna, Aurora, Aria, Teddy) para
   que lean su personalidad y estado de IA desde la base de datos del
   panel en vez de solo su código fijo — con el código como respaldo
   si la base de datos no responde.
3. Registro de actividad / logs visibles desde el panel (tabla
   `bot_events`, ya creada en la base de datos, todavía sin pantalla).
4. Definir si/cómo los bots conversan entre ellos (con límites de
   turnos y frecuencia, igual que se planeó para TAMAGO).
