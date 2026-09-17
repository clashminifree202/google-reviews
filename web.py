from __future__ import annotations
import asyncio, secrets, time
from typing import Any
from aiohttp import ClientTimeout, web
from config import settings
from licensing import FREE_DAILY, clean_phone

SESSION_COOKIE = "session"

CSS = (
    "body{font-family:system-ui,sans-serif;background:#0a0e16;color:#e8ecf4;"
    "margin:0;font-size:14px}main{max-width:520px;margin:0 auto;padding:12px}"
    "h1{font-size:22px;margin:0 0 12px}"
    ".card{background:#141a2a;border:1px solid #1e2a42;border-radius:8px;"
    "padding:12px;margin:8px 0}"
    "input,button,textarea{font-size:14px;border-radius:6px;border:1px solid #2a3a5e;"
    "padding:8px;width:100%;box-sizing:border-box;margin:4px 0}"
    "input,textarea{background:#0a0e16;color:#e8ecf4}"
    "button{background:#1a73e8;color:#fff;border:0;cursor:pointer;font-weight:700}"
    "button.sec{background:#2a3a5e}"
    "a{color:#7fb3ff}.mut{color:#93a1b8;font-size:12px}.ok{color:#5fd97a}.err{color:#ff7a7a}"
    ".row{display:flex;gap:6px}.row>*{flex:1}"
    "code{background:#060a12;padding:1px 4px;border-radius:4px;word-break:break-all;font-size:13px}"
    ".msg{padding:6px 8px;border-radius:6px;margin:4px 0;max-width:85%;font-size:13px}"
    ".me{background:#1a73e8;margin-left:auto}.them{background:#1e2a42}"
    "img.chat{max-width:100%;border-radius:6px}"
    "footer{padding:8px 12px;font-size:11px;color:#93a1b8;text-align:center}"
)

JS_CHAT = """
let last=0;
async function poll(){try{const r=await fetch('/api/messages?since='+last);const d=await r.json();if(d.ok){for(const m of d.messages){add(m);last=Math.max(last,m.id);}}}catch(e){}setTimeout(poll,2000);}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function add(m){const w=document.getElementById('msgs');const d=document.createElement('div');d.className='msg '+(m.direction==='out'?'me':'them');let h='<b>'+esc(m.author||'')+'</b><br>'+esc(m.text||'').replace(/\\n/g,'<br>');if(m.image)h+='<br><img class=chat src='+m.image+'>';d.innerHTML=h;w.appendChild(d);w.scrollTop=w.scrollHeight;}
async function send(ev){ev.preventDefault();const t=document.getElementById('t');const f=document.getElementById('f');const fd=new FormData();fd.append('text',t.value);if(f.files[0])fd.append('photo',f.files[0]);t.value='';f.value='';await fetch('/api/send',{method:'POST',body:fd});}
window.onload=()=>{poll();document.getElementById('frm').onsubmit=send;};
"""

JS_APP = """
async function j(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})});return r.json();}
async function lookup(ev){ev.preventDefault();const out=document.getElementById('out');out.innerHTML='Buscando...';const d=await j('/api/lookup',{url:document.getElementById('url').value});if(!d.ok){out.innerHTML='<p class=err>'+d.error+'</p>'+(d.upgrade?upg():'');return;}if(d.choose){let h='<p>Varias coincidencias, elige:</p>';d.options.forEach((o,i)=>{h+='<div class=card><b>'+(i+1)+'. '+o.name+'</b><br>'+o.address+'<br><button onclick=\"pick(\\''+d.token+'\\','+i+')\">Elegir '+(i+1)+'</button></div>';});out.innerHTML=h;return;}show(d.data,out);updQuota();}
function upg(){return '<div class=card><b>Usaste tus 3 gratis de hoy.</b><br>Mejora tu plan por chat.<br><a href=\"/chat\"><button>Contactar</button></a></div>';}
function show(d,out){out.innerHTML='<div class=card><b>'+d.name+'</b><br>'+d.address+'<br>'+d.city+' '+(d.postal_code||'')+'<br><br>Place ID<br><code>'+d.place_id+'</code><br><br>Reseña<br><code>'+d.review_url+'</code><br><br>'+(d.where?'<p class=mut>'+d.where+'</p>':'')+'</div>';}
async function pick(token,index){const out=document.getElementById('out');const d=await j('/api/pick',{token,index});if(!d.ok){out.innerHTML='<p class=err>'+d.error+'</p>';return;}show(d.data,out);updQuota();}
async function updQuota(){const r=await fetch('/api/quota');const d=await r.json();if(d.ok)document.getElementById('q').textContent=d.left;}
updQuota();
"""

def page(title: str, body: str, js: str = "") -> web.Response:
    html = (
        "<!doctype html><html lang=es><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title><style>{CSS}</style></head><body>"
        "<main>"
        f"<h1>{title}</h1>{body}</main>"
        "<footer>Licencia requerida. Uso comercial registrado.</footer>"
        + (f"<script>{js}</script>" if js else "")
        + "</body></html>"
    )
    return web.Response(text=html, content_type="text/html")

async def current_user(request: web.Request):
    import bot as botmod
    token = request.cookies.get(SESSION_COOKIE, "")
    return await botmod.store.user_by_session(token)

def need_login():
    return web.json_response({"ok": False, "error": "Inicia sesión con tu teléfono."}, status=401)

async def index(_: web.Request) -> web.Response:
    import bot as botmod
    body = (
        "<div class=card><b>Place ID de Google Maps</b><br>"
        "Pega el enlace del negocio y recibe nombre, dirección, Place ID y reseña.</div>"
        "<div class=card><b>Gratis:</b> 3 negocios/24h.<br>"
        "<b>Plan PRO:</b> ilimitado con licencia.<br>"
        "<a href='/chat'><button>Contactar para plan</button></a></div>"
        "<div class=card><b>Entra con tu teléfono</b>"
        "<div class=row><input id=p placeholder='Teléfono (34...)'></div>"
        "<button onclick='go()'>Continuar</button><p class=mut id=msg></p></div>"
        "<script>"
        "async function j(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});return r.json();}"
        "async function go(){const p=document.getElementById('p').value;const d=await j('/api/login',{phone:p});const s=document.getElementById('step');const m=document.getElementById('msg');"
        "if(d.status==='confirm'){s.innerHTML='<p>¿Eres <b>'+d.name+'</b>?</p><button onclick=confirm()>Sí, soy yo</button>';m.textContent='';}"
        "else if(d.status==='new'){s.innerHTML='<input id=n placeholder=Nombre><input id=a placeholder=Apellidos><button onclick=reg()>Crear</button>';}"
        "else{m.textContent=d.error||'Error';}}"
        "async function reg(){const d=await j('/api/register',{phone:document.getElementById('p').value,first_name:document.getElementById('n').value,last_name:document.getElementById('a').value});"
        "if(d.ok)location.href='/app';else document.getElementById('msg').textContent=d.error;}"
        "async function confirm(){const d=await j('/api/confirm',{phone:document.getElementById('p').value});"
        "if(d.ok)location.href='/app';else document.getElementById('msg').textContent=d.error;}"
        "</script>"
    )
    return page("Place ID — Licencia", body)

async def app_page(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        raise web.HTTPFound("/")
    body = (
        f"<p>Hola, <b>{user['first_name']}</b> · <code>{user['phone']}</code> · "
        "<b id=q>…</b> gratis hoy.</p>"
        "<div class=card><form onsubmit='lookup(event)'>"
        "<input id=url placeholder='https://maps.app.goo.gl/...'>"
        "<button>Buscar Place ID</button></form></div>"
        "<div id=out></div>"
        "<script>" + JS_APP + "</script>"
    )
    return page("Panel", body)

async def chat_page(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        raise web.HTTPFound("/")
    body = (
        "<div id=msgs style='min-height:30vh'></div>"
        "<form id=frm><textarea id=t rows=2 placeholder='Escribe...'></textarea>"
        "<input type=file id=f accept='image/*'><button>Enviar</button></form>"
    )
    return page("Chat", body, JS_CHAT)

async def redeem_page(_: web.Request) -> web.Response:
    body = (
        "<div class=card><input id=k placeholder='Licencia (RBL-...)'>"
        "<div class=row><input id=n placeholder=Nombre><input id=a placeholder=Apellidos></div>"
        "<input id=p placeholder='Teléfono'>"
        "<input id=w placeholder='Webhook para resultados (opcional)'>"
        "<button onclick='go()'>Canjear</button><p class=mut id=m></p></div>"
        "<script>"
        "async function go(){const b={key:document.getElementById('k').value,"
        "first_name:document.getElementById('n').value,"
        "last_name:document.getElementById('a').value,"
        "phone:document.getElementById('p').value,"
        "webhook:document.getElementById('w').value};"
        "const r=await fetch('/api/redeem',{method:'POST',headers:"
        "{'Content-Type':'application/json'},body:JSON.stringify(b)});"
        "const d=await r.json();"
        "document.getElementById('m').textContent=d.ok?'Licencia activada. Ya puedes entrar.':'Error: '+d.error;"
        "if(d.ok)setTimeout(()=>location.href='/app',1200);}"
        "</script>"
    )
    return page("Canjear licencia", body)

async def account_page(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        raise web.HTTPFound("/")
    wh = user.get("result_webhook") or ""
    body = (
        f"<div class=card><b>{user['first_name']} {user['last_name']}</b><br>"
        f"<code>{user['phone']}</code></div>"
        "<div class=card><b>¿Dónde quieres recibir resultados?</b>"
        f"<input id=w placeholder='https://discord.com/api/webhooks/...' value='{wh}'>"
        "<button onclick='save()'>Guardar</button>"
        "<p class=mut>Vacío = se entregan aquí en la web.</p>"
        "<p class=mut id=m></p></div>"
        "<form method=post action='/api/logout' style='display:inline'>"
        "<button class=sec formaction='/api/logout'>Cerrar sesión</button></form>"
        "<script>"
        "async function save(){const r=await fetch('/api/settings',"
        "{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({webhook:document.getElementById('w').value})});"
        "const d=await r.json();document.getElementById('m').textContent=d.ok?'Guardado.':'Error';}</script>"
    )
    return page("Cuenta", body)

async def api_login(request: web.Request):
    import bot as botmod
    data = await request.json()
    phone = clean_phone(data.get("phone", ""))
    user = await botmod.store.get_user(phone)
    if not user:
        return web.json_response({"ok": True, "status": "new"})
    name = f"{user['first_name']} {user['last_name']}".strip()
    return web.json_response({"ok": True, "status": "confirm", "name": name})

async def api_register(request: web.Request):
    import bot as botmod
    data = await request.json()
    res = await botmod.store.register(data.get("phone", ""), data.get("first_name", ""), data.get("last_name", ""))
    if not res["ok"]:
        return web.json_response(res)
    resp = web.json_response({"ok": True})
    resp.set_cookie(SESSION_COOKIE, res["token"], httponly=True, samesite="lax")
    return resp

async def api_confirm(request: web.Request):
    import bot as botmod
    data = await request.json()
    token = await botmod.store.login_token(clean_phone(data.get("phone", "")))
    if not token:
        return web.json_response({"ok": False, "error": "Teléfono no registrado."})
    resp = web.json_response({"ok": True})
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
    return resp

async def api_logout(request: web.Request):
    import bot as botmod
    await botmod.store.logout(request.cookies.get(SESSION_COOKIE, ""))
    raise web.HTTPFound("/")

async def api_quota(request: web.Request):
    import bot as botmod
    user = await current_user(request)
    if not user:
        return need_login()
    left = await botmod.store.quota_left(user["phone"])
    licensed = await botmod.store.licensed(user["phone"])
    return web.json_response({"ok": True, "left": left, "licensed": licensed})

async def api_history(request: web.Request):
    import bot as botmod
    user = await current_user(request)
    if not user:
        return need_login()
    items = await botmod.store.history(user["phone"])
    return web.json_response({"ok": True, "items": items})

async def api_settings(request: web.Request):
    import bot as botmod
    user = await current_user(request)
    if not user:
        return need_login()
    if request.method == "GET":
        return web.json_response({"ok": True, "webhook": user.get("result_webhook") or ""})
    data = await request.json()
    await botmod.store.set_webhook(user["phone"], data.get("webhook", ""))
    return web.json_response({"ok": True})

async def deliver(user: dict, data: dict[str, Any]) -> str:
    import bot as botmod
    wh = (user.get("result_webhook") or "").strip()
    if not wh or botmod.session is None:
        return "Entregado aquí en la web."
    text = f"**{data['name']}**\n{data['address']}\n{data['city']} {data.get('postal_code') or ''}\nPlace ID: `{data['place_id']}`\n{data['review_url']}"
    try:
        async with botmod.session.post(wh, json={"content": text[:1900]}, timeout=ClientTimeout(total=10)) as resp:
            if resp.status in (200, 204):
                return "Enviado a tu webhook."
    except Exception:
        pass
    return "Tu webhook falló; entregado aquí en la web."

async def api_lookup(request: web.Request):
    import bot as botmod
    user = await current_user(request)
    if not user:
        return need_login()
    phone = user["phone"]
    if await botmod.store.quota_left(phone) <= 0:
        return web.json_response({"ok": False, "upgrade": True, "error": "Has usado tus 3 gratis de hoy. Mejora tu plan."})
    data = await request.json()
    url = (data.get("url") or "").strip()
    try:
        outcome = await asyncio.wait_for(botmod.run_lookup(url, 0), timeout=settings.overall_timeout)
    except asyncio.TimeoutError:
        return web.json_response({"ok": False, "error": "La búsqueda ha tardado demasiado."})
    if outcome["kind"] == "error":
        return web.json_response({"ok": False, "error": outcome["message"]})
    if outcome["kind"] == "choose":
        token = secrets.token_urlsafe(8)
        botmod.pending[token] = {"user_id": 0, "phone": phone, "options": outcome["options"], "cache_key": url, "expires": time.time() + settings.selection_timeout}
        return web.json_response({"ok": True, "choose": True, "options": outcome["options"], "token": token})
    res = outcome["data"]
    await botmod.store.log_lookup(phone, url, res["place_id"])
    where = await deliver(user, res)
    res = dict(res); res["where"] = where
    return web.json_response({"ok": True, "data": res})

async def api_pick(request: web.Request):
    import bot as botmod
    user = await current_user(request)
    if not user:
        return need_login()
    data = await request.json()
    entry = botmod.pending.get(data.get("token", ""))
    if not entry or entry.get("phone") != user["phone"]:
        return web.json_response({"ok": False, "error": "Selección caducada."})
    idx = data.get("index", -1)
    if not isinstance(idx, int) or idx >= len(entry["options"]):
        return web.json_response({"ok": False, "error": "Opción no válida."})
    res = entry["options"][idx]
    botmod.pending.pop(data.get("token", ""), None)
    await botmod.store.log_lookup(user["phone"], entry["cache_key"], res["place_id"])
    await botmod.cache.set(entry["cache_key"], botmod.result_to_dict(res))
    where = await deliver(user, res)
    res = dict(res); res["where"] = where
    return web.json_response({"ok": True, "data": res})

async def api_redeem(request: web.Request):
    import bot as botmod
    data = await request.json()
    res = await botmod.store.redeem(data.get("key", ""), data.get("first_name", ""), data.get("last_name", ""), data.get("phone", ""))
    if not res["ok"]:
        return web.json_response(res)
    phone = res["phone"]
    wh = (data.get("webhook") or "").strip()
    if wh:
        await botmod.store.set_webhook(phone, wh)
    try:
        channel = await botmod.ensure_user_channel(phone, res["first_name"], res["last_name"])
        await channel.send(f"Licencia canjeada: `{res['key']}` ({res['plan']}) por {res['first_name']} {res['last_name']}.")
    except Exception as exc:
        botmod.log.info("Sin canal Discord: %s", type(exc).__name__)
    await botmod.post_sales_webhook(res)
    token = await botmod.store.login_token(phone)
    resp = web.json_response({"ok": True})
    if token:
        resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
    return resp

async def api_messages(request: web.Request):
    import bot as botmod
    user = await current_user(request)
    if not user:
        return need_login()
    try:
        since = int(request.query.get("since", "0"))
    except ValueError:
        since = 0
    msgs = await botmod.store.get_messages(user["phone"], since)
    return web.json_response({"ok": True, "messages": msgs})

async def api_send(request: web.Request):
    import bot as botmod
    user = await current_user(request)
    if not user:
        return need_login()
    phone = user["phone"]
    post = await request.post()
    text = (post.get("text") or "").strip()
    image_bytes = None
    filename = "foto.jpg"
    photo = post.get("photo")
    if photo is not None and getattr(photo, "file", None):
        filename = getattr(photo, "filename", filename) or filename
        image_bytes = photo.file.read(6 * 1024 * 1024)
    if not text and not image_bytes:
        return web.json_response({"ok": False, "error": "Mensaje vacío."})
    ok = await botmod.send_to_user(phone, text, image_bytes, filename, author_name=f"{user['first_name']} {user['last_name']}")
    if not ok:
        return web.json_response({"ok": False, "error": "Aún no tienes canal. Habla primero por el chat."})
    return web.json_response({"ok": True})

async def healthz(_: web.Request) -> web.Response:
    return web.Response(text="ok")

def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/app", app_page)
    app.router.add_get("/chat", chat_page)
    app.router.add_get("/canjear", redeem_page)
    app.router.add_get("/cuenta", account_page)
    app.router.add_post("/api/login", api_login)
    app.router.add_post("/api/register", api_register)
    app.router.add_post("/api/confirm", api_confirm)
    app.router.add_post("/api/logout", api_logout)
    app.router.add_get("/api/quota", api_quota)
    app.router.add_get("/api/history", api_history)
    app.router.add_get("/api/settings", api_settings)
    app.router.add_post("/api/settings", api_settings)
    app.router.add_post("/api/lookup", api_lookup)
    app.router.add_post("/api/pick", api_pick)
    app.router.add_post("/api/redeem", api_redeem)
    app.router.add_get("/api/messages", api_messages)
    app.router.add_post("/api/send", api_send)
    app.router.add_get("/healthz", healthz)
    return app

_runner = None
async def start_web() -> None:
    global _runner
    _runner = web.AppRunner(create_app())
    await _runner.setup()
    await web.TCPSite(_runner, "0.0.0.0", settings.port).start()

async def stop_web() -> None:
    global _runner
    if _runner is not None:
        await _runner.cleanup()
        _runner = None
