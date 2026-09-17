# Place ID — Licencia

Web de licencias con búsqueda de Place ID de Google Maps y chat
con Discord. Sistema de licencias: 3 búsquedas gratis/24h, plan PRO
por chat de Discord.

## Despliegue

### Netlify (Docker)

1. Sube el proyecto a GitHub.
2. En https://app.netlify.com pulsa **Add new site > Import from Git**.
3. Selecciona el repositorio.
4. En **Build settings**, Netlify detecta el `Dockerfile` automáticamente.
5. Ve a **Site settings > Environment** y añade:

| Clave | Valor |
|---|---|
| `DISCORD_TOKEN` | Token del bot |
| `PROVIDER` | `finder` |
| `GOOGLE_API_KEY` | (vacío con finder) |
| `SALES_WEBHOOK_URL` | `https://discord.com/api/webhooks/1549913214660116553/cjU12LbwGSmInkfFSytO0hKFN1--yjIYa7mHfmklyIWQqOcspzsyyJ1VzxVjQT5u_nyP` |
| `GUILD_ID` | `1376191955511410688` |
| `SALES_CATEGORY_ID` | `1390861758880682055` |
| `OWNER_ID` | `1306929787033354250` |
| `OWNER_NAME` | `Marcos V.` |
| `CACHE_TTL` | `86400` |
| `MAX_RESULTS` | `5` |

6. **Build & deploy**. La web estará en `https://<tu-sitio>.netlify.app`.

### Render

Usa el `render.yaml` incluido (runtime Docker con Chromium).

### Local

```bat
copy .env.example .env
pip install -r requirements.txt
python bot.py
```

## Uso

- **Web**: entra en la URL, introduce tu teléfono para iniciar sesión.
- **3 búsquedas gratis/24h**. Para más, contacta por chat en Discord.
- **Canjear licencia**: `/canjear` con clave RBL-XXXX.
- **Comandos Discord** (solo owner): `,genkey`, `,delkey`.

## Estructura

```text
google-placeid-bot/
├── bot.py            # Discord: slash commands, chat, webhooks
├── config.py         # Configuración centralizada (.env)
├── finder.py         # Proveedor sin API (Place ID Finder + Chromium)
├── google_places.py  # Proveedor alternativo: Places API oficial
├── maps.py           # Validación y parseo de URLs
├── matching.py       # Puntuación y enlace de reseña
├── cache.py          # Caché SQLite con TTL
├── web.py            # Servidor web: login, panel, chat, licencias
├── licensing.py      # Usuarios, licencias, cuota, mensajes
├── requirements.txt
├── Dockerfile
├── netlify.toml
├── render.yaml
├── .env.example
└── .gitignore
```
