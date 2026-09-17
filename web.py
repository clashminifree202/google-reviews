from __future__ import annotations
import asyncio, secrets, time
from typing import Any
from aiohttp import ClientTimeout, web
from config import settings
from licensing import FREE_DAILY, clean_phone

SESSION_COOKIE = "session"

CSS = (
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');"
    "*{margin:0;padding:0;box-sizing:border-box}"
    "body{font-family:'Inter',system-ui,sans-serif;background:#070b14;color:#e8ecf4;"
    "min-height:100vh;font-size:15px}"
    "nav{display:flex;justify-content:space-between;align-items:center;"
    "padding:16px 32px;background:rgba(10,14,22,0.9);backdrop-filter:blur(20px);"
    "border-bottom:1px solid rgba(30,42,66,0.5);position:sticky;top:0;z-index:100}"
    "nav .logo{font-size:20px;font-weight:800;background:linear-gradient(135deg,#1a73e8,#7c3aed);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent}"
    "nav a{color:#93a1b8;text-decoration:none;font-size:14px;font-weight:500;"
    "padding:6px 14px;border-radius:8px;transition:all .2s}"
    "nav a:hover{color:#e8ecf4;background:rgba(26,115,232,0.1)}"
    "nav a.active{color:#1a73e8;background:rgba(26,115,232,0.15)}"
    "main{max-width:720px;margin:0 auto;padding:32px 16px}"
    "hero{text-align:center;padding:64px 0 48px}"
    "hero h1{font-size:42px;font-weight:800;line-height:1.2;margin-bottom:16px;"
    "background:linear-gradient(135deg,#e8ecf4,#7fb3ff);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent}"
    "hero p{font-size:18px;color:#93a1b8;max-width:520px;margin:0 auto 32px;line-height:1.6}"
    ".badge{display:inline-block;background:linear-gradient(135deg,rgba(26,115,232,0.2),"
    "rgba(124,58,237,0.2));border:1px solid rgba(26,115,232,0.3);border-radius:20px;"
    "padding:6px 16px;font-size:13px;color:#7fb3ff;margin-bottom:20px}"
    ".hero-buttons{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}"
    "btn{display:inline-flex;align-items:center;gap:8px;font-family:'Inter',sans-serif;"
    "font-size:15px;font-weight:600;padding:14px 28px;border-radius:12px;border:none;"
    "cursor:pointer;transition:all .3s;text-decoration:none}"
    "btn.primary{background:linear-gradient(135deg,#1a73e8,#7c3aed);color:#fff;"
    "box-shadow:0 4px 20px rgba(26,115,232,0.4)}"
    "btn.primary:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(26,115,232,0.6)}"
    "btn.ghost{background:rgba(255,255,255,0.05);color:#e8ecf4;"
    "border:1px solid rgba(255,255,255,0.1)}"
    "btn.ghost:hover{background:rgba(255,255,255,0.1)}"
    "section{margin:32px 0}"
    "section h2{font-size:28px;font-weight:700;margin-bottom:8px}"
    "section .sub{color:#93a1b8;font-size:16px;margin-bottom:24px}"
    ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin:24px 0}"
    ".card{background:linear-gradient(135deg,rgba(20,26,42,0.8),rgba(14,20,34,0.9));"
    "border:1px solid rgba(30,42,66,0.6);border-radius:16px;padding:24px;"
    "transition:all .3s;position:relative;overflow:hidden}"
    ".card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;"
    "background:linear-gradient(90deg,#1a73e8,#7c3aed);opacity:0;transition:opacity .3s}"
    ".card:hover::before{opacity:1}"
    ".card:hover{border-color:rgba(26,115,232,0.3);transform:translateY(-4px);"
    "box-shadow:0 12px 40px rgba(0,0,0,0.4)}"
    ".card .icon{font-size:32px;margin-bottom:12px}"
    ".card h3{font-size:18px;font-weight:600;margin-bottom:8px}"
    ".card p{color:#93a1b8;font-size:14px;line-height:1.5}"
    ".card .price{font-size:24px;font-weight:700;margin-top:12px}"
    ".card .price span{font-size:13px;font-weight:400;color:#93a1b8}"
    ".card.popular{border-color:rgba(124,58,237,0.4)}"
    ".card.popular::before{opacity:1}"
    ".card.popular .tag{position:absolute;top:12px;right:12px;background:"
    "linear-gradient(135deg,#7c3aed,#1a73e8);color:#fff;font-size:11px;"
    "font-weight:600;padding:4px 10px;border-radius:20px}"
    ".features{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;"
    "margin:24px 0}"
    ".feature{text-align:center;padding:24px;background:rgba(20,26,42,0.5);"
    "border-radius:12px;border:1px solid rgba(30,42,66,0.4)}"
    ".feature .icon{font-size:28px;margin-bottom:8px}"
    ".feature h4{font-size:15px;font-weight:600;margin-bottom:4px}"
    ".feature p{font-size:13px;color:#93a1b8}"
    "input,textarea,select{font-family:'Inter',sans-serif;font-size:14px;"
    "border-radius:10px;border:1px solid rgba(42,58,94,0.8);padding:12px 16px;"
    "width:100%;box-sizing:border-box;margin:6px 0;background:rgba(10,14,22,0.8);"
    "color:#e8ecf4;transition:border-color .2s}"
    "input:focus,textarea:focus{border-color:#1a73e8;outline:none;"
    "box-shadow:0 0 0 3px rgba(26,115,232,0.15)}"
    "input::placeholder,textarea::placeholder{color:#4a5568}"
    ".row{display:flex;gap:12px}.row>*{flex:1}"
    "code{background:rgba(6,10,18,0.8);padding:2px 8px;border-radius:6px;"
    "word-break:break-all;font-size:13px;color:#7fb3ff}"
    ".msg{padding:10px 14px;border-radius:12px;margin:6px 0;max-width:85%;"
    "font-size:14px;line-height:1.5}"
    ".me{background:linear-gradient(135deg,rgba(26,115,232,0.3),rgba(124,58,237,0.2));"
    "margin-left:auto;border-bottom-right-radius:4px}"
    ".them{background:rgba(20,26,42,0.8);border-bottom-left-radius:4px}"
    ".chat-box{background:rgba(10,14,22,0.5);border:1px solid rgba(30,42,66,0.6);"
    "border-radius:16px;padding:20px;min-height:400px;margin-bottom:16px;"
    "overflow-y:auto}"
    "#msgs{min-height:300px}"
    "img.chat{max-width:100%;border-radius:12px;max-height:300px}"
    "footer{padding:32px;text-align:center;color:#4a5568;font-size:13px;"
    "border-top:1px solid rgba(30,42,66,0.3);margin-top:64px}"
    "footer a{color:#7fb3ff}"
    ".toast{position:fixed;bottom:24px;right:24px;background:#1a73e8;color:#fff;"
    "padding:14px 24px;border-radius:12px;font-weight:600;font-size:14px;"
    "box-shadow:0 8px 30px rgba(0,0,0,0.4);transform:translateY(100px);opacity:0;"
    "transition:all .3s;z-index:999}"
    ".toast.show{transform:translateY(0);opacity:1}"
    ".divider{height:1px;background:linear-gradient(90deg,transparent,"
    "rgba(30,42,66,0.8),transparent);margin:32px 0}"
    ".stat{text-align:center;padding:32px}.stat .number{font-size:48px;font-weight:800;"
    "background:linear-gradient(135deg,#1a73e8,#7c3aed);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent}"
    ".stat .label{color:#93a1b8;font-size:14px;margin-top:4px}"
    "@media(max-width:640px){hero h1{font-size:30px}.cards{grid-template-columns:1fr}"
    "nav{padding:12px 16px}main{padding:16px}}"
)

JS_CHAT = """
let last=0;
async function poll(){try{const r=await fetch('/api/messages?since='+last);const d=await r.json();if(d.ok){for(const m of d.messages){add(m);last=Math.max(last,m.id);}}}catch(e){}setTimeout(poll,2000);}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function add(m){const w=document.getElementById('msgs');const d=document.createElement('div');d.className='msg '+(m.direction==='out'?'me':'them');let h='<b>'+esc(m.author||'')+'</b>';if(m.text)h+='<br>'+esc(m.text).replace(/\\n/g,'<br>');if(m.image)h+='<br><img class=chat src='+m.image+'>';d.innerHTML=h;w.appendChild(d);w.scrollTop=w.scrollHeight;}
async function send(ev){ev.preventDefault();const t=document.getElementById('t');const f=document.getElementById('f');const fd=new FormData();fd.append('text',t.value);if(f.files[0])fd.append('photo',f.files[0]);t.value='';f.value='';await fetch('/api/send',{method:'POST',body:fd});}
window.onload=()=>{poll();document.getElementById('frm').onsubmit=send;};
"""

JS_APP = """
async function j(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})});return r.json();}
async function lookup(ev){ev.preventDefault();const out=document.getElementById('out');out.innerHTML='<div style=text-align:center;padding:20px><div class=spinner></div>Buscando...</div>';const d=await j('/api/lookup',{url:document.getElementById('url').value});if(!d.ok){out.innerHTML='<p class=err>'+d.error+'</p>'+(d.upgrade?upg():'');return;}if(d.choose){let h='<p>Varias coincidencias, elige:</p>';d.options.forEach((o,i)=>{h+='<div class=card><h3>'+(i+1)+'. '+o.name+'</h3><p>'+o.address+'</p><button class=primary onclick=pick(\\''+d.token+'\\','+i+')\">Seleccionar</button></div>';});out.innerHTML=h;return;}show(d.data,out);updQuota();}
function upg(){return '<div class=card><h3>Limitado a 3 busquedas hoy</h3><p>Mejora tu plan por chat</p><a href=/chat><btn class=primary>Contactar</btn></a></div>';}
function show(d,out){out.innerHTML='<div class=card><h3>'+d.name+'</h3><p>'+d.address+'<br>'+d.city+' '+(d.postal_code||'')+'</p><code>Place ID: '+d.place_id+'</code><br><a href=\"'+d.review_url+'\" target=_blank><btn class=primary>Abrir reseña</btn></a>'+(d.where?'<p class=mut>'+d.where+'</p>':'')+'</div>';}
async function pick(token,index){const out=document.getElementById('out');const d=await j('/api/pick',{token,index});if(!d.ok){out.innerHTML='<p class=err>'+d.error+'</p>';return;}show(d.data,out);updQuota();}
async function updQuota(){const r=await fetch('/api/quota');const d=await r.json();if(d.ok)document.getElementById('q').textContent=d.left;}
updQuota();
"""

def page(title: str, body: str, js: str = "") -> web.Response:
    html = (
        "<!doctype html><html lang=es><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title><style>{CSS}</style></head><body>"
        "<nav><span class=logo>Place ID</span>"
        "<div><a href='/' class=active>Inicio</a>"
        "<a href='/app'>Panel</a><a href='/chat'>Chat</a>"
        "<a href='/cuenta'>Cuenta</a></div></nav>"
        "<main>" + body + "</main>"
        "<footer>Place ID Bot — Licencia requerida para uso comercial. "
        "<a href='https://discord.gg'>Contacto</a></footer>"
        "<div class=toast id=toast></div>"
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
    body = (
        "<section hero>"
        "<div class=badge>Licencia requerida</div>"
        "<h1>Place ID de Google Maps</h1>"
        "<p>Convierte cualquier enlace de Google Maps en el Place ID exacto "
        "y el enlace directo de reseña en segundos.</p>"
        "<div class=hero-buttons>"
        "<a href='/canjear' class='btn primary'>Canjear Licencia</a>"
        "<a href='/app' class='btn ghost'>Entrar con Teléfono</a>"
        "</div></section>"
        "<div class=divider></div>"
        "<div class=stats>"
        "<div class=stat><div class=number>3</div><div class=label>Búsquedas gratis / 24h</div></div>"
        "<div class=stat><div class=number>∞</div><div class=label>Plan PRO ilimitado</div></div>"
        "<div class=stat><div class=number>📱</div><div class=label>Chat instantáneo</div></div>"
        "</div>"
        "<section><h2>¿Cómo funciona?</h2>"
        "<div class=features>"
        "<div class=feature><div class=icon>🔍</div><h4>Busca</h4><p>Pega un enlace de Google Maps</p></div>"
        "<div class=feature><div class=icon>📋</div><h4>Recibe</h4><p>Place ID y enlace de reseña</p></div>"
        "<div class=feature><div class=icon>⚡</div><h4>Instantáneo</h4><p>Resultado en segundos</p></div>"
        "</div></section>"
        "<section><div class=divider></div>"
        "<div class=cards>"
        "<div class=card><div class=icon>🆓</div><h3>Gratis</h3>"
        "<p>3 búsquedas cada 24 horas</p>"
        "<div class=price>0<span> / mes</span></div></div>"
        "<div class=card popular><span class=tag>PRO</span><div class=icon>⚡</div><h3>PRO</h3>"
        "<p>Búsquedas ilimitadas + chat + webhook propio</p>"
        "<div class=price>Contactar<span> por chat</span></div></div>"
        "</div></section>"
        "<section><h2>Contacto</h2>"
        "<p style='color:#93a1b8'>Para contratar el plan PRO o cualquier duda, "
        "contacta por Discord:</p>"
        "<a href='https://discord.gg' target=_blank><btn class='btn primary'>Discord — Soporte</btn></a>"
        "</section>"
    )
    return page("Place ID", body)

async def app_page(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        raise web.HTTPFound("/")
    body = (
        f"<div class=card style='margin-bottom:24px'>"
        f"<h3 style='margin-bottom:4px'>Hola, {user['first_name']}</h3>"
        f"<p style='color:#93a1b8'><code>{user['phone']}</code> · "
        f"<b id=q>Cargando...</b> gratis hoy</p></div>"
        "<div class=card><form onsubmit='lookup(event)' style='display:flex;gap:8px'>"
        "<input id=url placeholder='https://maps.app.goo.gl/...' style='flex:1'>"
        "<button type=submit class='btn primary' style='width:auto'>Buscar</button>"
        "</form></div>"
        "<div id=out></div>"
        "<script>" + JS_APP + "</script>"
    )
    return page("Panel", body)

async def chat_page(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        raise web.HTTPFound("/")
    body = (
        "<div id=msgs class=chat-box></div>"
        "<form id=frm style='display:flex;gap:8px'>"
        "<textarea id=t rows=1 placeholder='Escribe un mensaje...' "
        "style='flex:1'></textarea>"
        "<input type=file id=f accept='image/*' style='width:auto'>"
        "<button type=submit class='btn primary' style='width:auto'>Enviar</button>"
        "</form>"
        "<script>" + JS_CHAT + "</script>"
    )
    return page("Chat", body)

async def redeem_page(_: web.Request) -> web.Response:
    body = (
        "<div class=card><h2>Canjear Licencia</h2>"
        "<input id=k placeholder='Licencia (RBL-...)'>"
        "<div class=row><input id=n placeholder='Nombre'><input id=a placeholder='Apellidos'></div>"
        "<input id=p placeholder='Teléfono'>"
        "<input id=w placeholder='Webhook para resultados (opcional)'>"
        "<button onclick='go()' class='btn primary'>Canjear</button>"
        "<p class=mut id=m></p></div>"
        "<script>"
        "async function go(){const b={key:document.getElementById('k').value,"
        "first_name:document.getElementById('n').value,"
        "last_name:document.getElementById('a').value,"
        "phone:document.getElementById('p').value,"
        "webhook:document.getElementById('w').value};"
        "const r=await fetch('/api/redeem',{method:'POST',headers:"
        "{'Content-Type':'application/json'},body:JSON.stringify(b)});"
        "const d=await r.json();"
        "document.getElementById('m').textContent=d.ok?'✅ Licencia activada.':'❌ '+d.error;"
        "if(d.ok)setTimeout(()=>location.href='/app',1200);}"
        "</script>"
    )
    return page("Canjear Licencia", body)

async def account_page(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        raise web.HTTPFound("/")
    wh = user.get("result_webhook") or ""
    body = (
        f"<div class=card><h3>{user['first_name']} {user['last_name']}</h3>"
        f"<p style='color:#93a1b8'><code>{user['phone']}</code></p></div>"
        "<div class=card><h3>¿Dónde recibes resultados?</h3>"
        "<input id=w placeholder='https://discord.com/api/webhooks/...' value='{wh}'>"
        "<button onclick='save()' class='btn primary'>Guardar</button>"
        "<p class=mut>Vacío = se entregan aquí en la web.</p>"
        "<p class=mut id=m></p></div>"
        "<form method=post action='/api/logout'>"
        "<button type=submit class='btn ghost'>Cerrar sesión</button></form>"
        "<script>"
        "async function save(){const r=await fetch('/api/settings',"
        "{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({webhook:document.getElementById('w').value})});"
        "const d=await r.json();document.getElementById('m').textContent=d.ok?'✅ Guardado.':'Error';}</script>"
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
        return web.json_response({"ok": False, "upgrade": True, "error": "Has usado tus 3 gratis de hoy."})
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
