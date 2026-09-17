from __future__ import annotations
import asyncio, secrets, time
from typing import Any
from aiohttp import ClientTimeout, web
from config import settings
from licensing import FREE_DAILY, clean_phone

SESSION_COOKIE = "session"

CSS = (
    "*{margin:0;padding:0;box-sizing:border-box}"
    "html{scroll-behavior:smooth}"
    "body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;"
    "background:#080c18;color:#e0e6f0;min-height:100vh;font-size:16px;"
    "overflow-x:hidden}"
    "nav{display:flex;justify-content:space-between;align-items:center;"
    "padding:18px 40px;background:rgba(8,12,24,0.95);backdrop-filter:blur(20px);"
    "border-bottom:1px solid rgba(30,50,80,0.5);position:sticky;top:0;z-index:100}"
    "nav .logo{font-size:22px;font-weight:800;letter-spacing:-0.5px;"
    "background:linear-gradient(135deg,#3b82f6,#8b5cf6);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent}"
    "nav .logo small{font-size:11px;opacity:0.6;margin-left:4px}"
    "nav a{color:#8899aa;text-decoration:none;font-size:14px;font-weight:500;"
    "padding:8px 16px;border-radius:10px;transition:all .25s}"
    "nav a:hover,nav a.active{color:#e0e6f0;background:rgba(59,130,246,0.15)}"
    ".cta-btn{color:#fff!important;background:#3b82f6!important;"
    "font-weight:600!important;border-radius:10px!important;"
    "padding:8px 24px!important}"
    "main{max-width:900px;margin:0 auto;padding:0 20px}"
    ".hero{text-align:center;padding:100px 0 80px;position:relative}"
    ".hero::after{content:'';position:absolute;bottom:0;left:50%;transform:translateX(-50%);"
    "width:600px;height:1px;background:linear-gradient(90deg,transparent,"
    "rgba(59,130,246,0.3),transparent)}"
    ".hero .badge{display:inline-block;background:linear-gradient(135deg,"
    "rgba(59,130,246,0.15),rgba(139,92,246,0.15));"
    "border:1px solid rgba(59,130,246,0.25);border-radius:50px;"
    "padding:8px 20px;font-size:13px;color:#60a5fa;margin-bottom:24px;"
    "font-weight:500}"
    ".hero h1{font-size:56px;font-weight:800;line-height:1.1;margin-bottom:20px;"
    "letter-spacing:-1px}"
    ".hero h1 .grad{background:linear-gradient(135deg,#60a5fa,#a78bfa);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent}"
    ".hero p{font-size:20px;color:#8899aa;max-width:560px;margin:0 auto 36px;line-height:1.7}"
    ".hero .buttons{display:flex;gap:14px;justify-content:center;flex-wrap:wrap}"
    "btn{display:inline-flex;align-items:center;gap:8px;font-family:inherit;"
    "font-size:16px;font-weight:600;padding:16px 32px;border-radius:14px;"
    "border:none;cursor:pointer;transition:all .3s;text-decoration:none;"
    "letter-spacing:-0.2px}"
    "btn.primary{background:linear-gradient(135deg,#3b82f6,#8b5cf6);"
    "color:#fff;box-shadow:0 4px 24px rgba(59,130,246,0.35)}"
    "btn.primary:hover{transform:translateY(-3px);box-shadow:0 8px 32px rgba(59,130,246,0.5)}"
    "btn.ghost{background:rgba(255,255,255,0.04);color:#e0e6f0;"
    "border:1px solid rgba(255,255,255,0.08)}"
    "btn.ghost:hover{background:rgba(255,255,255,0.08);border-color:rgba(255,255,255,0.15)}"
    "section{padding:60px 0}"
    "section .section-title{font-size:36px;font-weight:800;margin-bottom:12px;"
    "letter-spacing:-0.5px}"
    "section .section-sub{color:#8899aa;font-size:17px;margin-bottom:40px;line-height:1.6}"
    ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}"
    ".card{background:linear-gradient(145deg,rgba(16,22,40,0.9),rgba(10,16,30,0.95));"
    "border:1px solid rgba(30,50,80,0.6);border-radius:20px;padding:28px;"
    "transition:all .35s;position:relative;overflow:hidden}"
    ".card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;"
    "background:linear-gradient(90deg,#3b82f6,#8b5cf6);opacity:0;transition:opacity .35s}"
    ".card:hover::before{opacity:1}"
    ".card:hover{border-color:rgba(59,130,246,0.3);transform:translateY(-6px);"
    "box-shadow:0 20px 60px rgba(0,0,0,0.5)}"
    ".card .icon{font-size:36px;margin-bottom:14px}"
    ".card h3{font-size:19px;font-weight:700;margin-bottom:8px}"
    ".card p{color:#8899aa;font-size:14px;line-height:1.6}"
    ".card .price{font-size:28px;font-weight:800;margin-top:16px}"
    ".card .price span{font-size:13px;font-weight:400;color:#8899aa}"
    ".card.popular{border-color:rgba(139,92,246,0.4)}"
    ".card.popular::before{opacity:1}"
    ".card.popular .tag{position:absolute;top:16px;right:16px;background:"
    "linear-gradient(135deg,#8b5cf6,#3b82f6);color:#fff;font-size:11px;"
    "font-weight:700;padding:5px 14px;border-radius:50px;text-transform:uppercase;"
    "letter-spacing:0.5px}"
    ".stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));"
    "gap:20px;margin:48px 0}"
    ".stat{text-align:center;padding:32px 16px;background:"
    "rgba(16,22,40,0.6);border-radius:16px;border:1px solid rgba(30,50,80,0.4)}"
    ".stat .number{font-size:44px;font-weight:900;line-height:1;"
    "background:linear-gradient(135deg,#3b82f6,#8b5cf6);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent}"
    ".stat .label{color:#8899aa;font-size:13px;margin-top:8px}"
    ".divider{height:1px;background:linear-gradient(90deg,transparent,"
    "rgba(59,130,246,0.2),transparent);margin:48px 0}"
    "input,textarea{font-family:inherit;font-size:15px;"
    "border-radius:12px;border:1px solid rgba(40,60,100,0.8);padding:14px 18px;"
    "width:100%;box-sizing:border-box;margin:8px 0;background:rgba(8,12,24,0.8);"
    "color:#e0e6f0;transition:border-color .2s,box-shadow .2s}"
    "input:focus,textarea:focus{border-color:#3b82f6;outline:none;"
    "box-shadow:0 0 0 4px rgba(59,130,246,0.15)}"
    "input::placeholder,textarea::placeholder{color:#4a5568}"
    ".row{display:flex;gap:12px}.row>*{flex:1}"
    "code{background:rgba(6,10,20,0.9);padding:2px 10px;border-radius:8px;"
    "word-break:break-all;font-size:13px;color:#60a5fa;border:1px solid rgba(59,130,246,0.2)}"
    ".msg{padding:12px 16px;border-radius:14px;margin:8px 0;max-width:85%;"
    "font-size:14px;line-height:1.6}"
    ".me{background:linear-gradient(135deg,rgba(59,130,246,0.25),"
    "rgba(139,92,246,0.15));margin-left:auto;border-bottom-right-radius:4px}"
    ".them{background:rgba(16,22,40,0.9);border-bottom-left-radius:4px}"
    ".chat-box{background:rgba(8,12,24,0.6);border:1px solid rgba(30,50,80,0.6);"
    "border-radius:20px;padding:24px;min-height:420px;margin-bottom:16px;"
    "overflow-y:auto;max-height:60vh}"
    "img.chat{max-width:100%;border-radius:14px;max-height:320px}"
    "footer{padding:40px 20px;text-align:center;color:#4a5568;font-size:13px;"
    "border-top:1px solid rgba(30,50,80,0.3);margin-top:60px}"
    "footer a{color:#60a5fa}"
    ".toast{position:fixed;bottom:24px;right:24px;background:#3b82f6;color:#fff;"
    "padding:14px 28px;border-radius:14px;font-weight:600;font-size:14px;"
    "box-shadow:0 8px 30px rgba(0,0,0,0.5);transform:translateY(100px);opacity:0;"
    "transition:all .3s;z-index:999}"
    ".toast.show{transform:translateY(0);opacity:1}"
    ".login-box{max-width:420px;margin:40px auto;padding:40px;"
    "background:linear-gradient(145deg,rgba(16,22,40,0.95),"
    "rgba(10,16,30,0.98));border-radius:24px;border:1px solid rgba(30,50,80,0.6)"
    "box-shadow:0 20px 60px rgba(0,0,0,0.4)}"
    ".login-box h2{font-size:28px;font-weight:800;margin-bottom:8px}"
    ".login-box p{color:#8899aa;font-size:15px;margin-bottom:24px}"
    ".login-box input{margin-bottom:4px}"
    "nav .menu-mobile{display:none}"
    "@keyframes fadeIn{from{opacity:0;transform:translateY(20px)}"
    "to{opacity:1;transform:translateY(0)}}"
    ".fade-in{animation:fadeIn .6s ease forwards}"
    "@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}"
    ".pulse{animation:pulse 2s infinite}"
    ".spinner{width:20px;height:20px;border:3px solid rgba(255,255,255,0.3);"
    "border-top-color:#fff;border-radius:50%;animation:spin 0.8s linear infinite;display:inline-block}"
    "@keyframes spin{to{transform:rotate(360deg)}}"
    "@media(max-width:768px){.hero h1{font-size:34px}"
    ".hero{padding:60px 0 40px}nav{padding:12px 16px}"
    "main{padding:0 12px}.cards{grid-template-columns:1fr}"
    ".stats{grid-template-columns:1fr 1fr}.login-box{margin:20px;padding:24px}}"
)

JS_CHAT = """
let last=0;
async function poll(){try{const r=await fetch('/api/messages?since='+last);const d=await r.json();if(d.ok){for(const m of d.messages){add(m);last=Math.max(last,m.id);}}}catch(e){}setTimeout(poll,2000);}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function add(m){const w=document.getElementById('msgs');const d=document.createElement('div');d.className='msg '+(m.direction==='out'?'me':'them');let h='<b>'+esc(m.author||'')+'</b>';if(m.text)h+='<br>'+esc(m.text).replace(/\\n/g,'<br>');if(m.image)h+='<br><img class=chat src='+m.image+'>';d.innerHTML=h;w.appendChild(d);w.scrollTop=w.scrollHeight;}
async function send(ev){ev.preventDefault();const t=document.getElementById('t');const f=document.getElementById('f');const fd=new FormData();fd.append('text',t.value);if(f.files[0])fd.append('photo',f.files[0]);t.value='';f.value='';const btn=document.querySelector('#frm btn');btn.disabled=true;btn.innerHTML='<span class=spinner></span>';await fetch('/api/send',{method:'POST',body:fd});btn.disabled=false;btn.textContent='Enviar';}
window.onload=()=>{poll();document.getElementById('frm').onsubmit=send;};
"""

JS_APP = """
async function j(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})});return r.json();}
async function lookup(ev){ev.preventDefault();const out=document.getElementById('out');out.innerHTML='<div style=text-align:center;padding:30px><span class=spinner></span> Buscando...</div>';const d=await j('/api/lookup',{url:document.getElementById('url').value});if(!d.ok){out.innerHTML='<p class=err>'+d.error+'</p>'+(d.upgrade?upg():'');return;}if(d.choose){let h='<p style=margin-bottom:16px">Varias coincidencias, elige:</p>';d.options.forEach((o,i)=>{h+='<div class=card><h3>'+(i+1)+'. '+o.name+'</h3><p style=color:#8899aa;font-size:13px'>'+o.address+'</p><p style="color:#60a5fa;font-size:12px;margin-top:4px">'+o.place_id+'</p><button class=primary onclick=pick(\\''+d.token+'\\','+i+') style="margin-top:10px">Seleccionar</button></div>';});out.innerHTML=h;return;}show(d.data,out);updQuota();}
function upg(){return '<div class=card><h3>Limite de 3 busquedas alcanzado</h3><p>Contacta por chat para mejorar tu plan</p><a href="/chat" class="cta-btn">Chat de Soporte</a></div>';}
function show(d,out){out.innerHTML='<div class=card><h3>'+d.name+'</h3><p style="color:#8899aa;font-size:14px">'+d.address+'<br>'+d.city+' '+(d.postal_code||'')+'</p><code>Place ID: '+d.place_id+'</code><br><a href="'+d.review_url+'" target=_blank><button class=primary style="width:auto;margin-top:12px">Abrir Reseña</button></a>'+(d.where?'<p class=mut>'+d.where+'</p>':'')+'</div>';}
async function pick(token,index){const out=document.getElementById('out');const d=await j('/api/pick',{token,index});if(!d.ok){out.innerHTML='<p class=err>'+d.error+'</p>';return;}show(d.data,out);updQuota();}
async function updQuota(){const r=await fetch('/api/quota');const d=await r.json();if(d.ok){const q=document.getElementById('q');if(q)q.textContent=d.left+' gratis hoy';}}
updQuota();
"""

def page(title: str, body: str, js: str = "") -> web.Response:
    html = (
        "<!doctype html><html lang=es><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title><style>{CSS}</style></head><body>"
        "<nav><span class=logo>PlaceID<span small>Bot</span></span>"
        "<div><a href='/' class=active>Inicio</a>"
        "<a href='/canjear'>Canjear</a>"
        "<a href='/app' class=cta-btn>Panel</a></div></nav>"
        "<main>" + body + "</main>"
        "<footer>PlaceID Bot — Uso comercial con licencia. "
        "<a href='https://discord.gg'>Discord</a> | "
        "<a href='mailto:contacto@placeid.bot'>Contacto</a></footer>"
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
        "<div class=hero fade-in>"
        "<div class=badge>🔒 Sistema de licencias activo</div>"
        "<h1>PlaceID <span class=grad>de Google Maps</span></h1>"
        "<p>Convierte cualquier enlace de Google Maps en el Place ID exacto "
        "y el enlace directo de reseña en segundos.</p>"
        "<div class=buttons>"
        "<a href='/canjear' class='btn primary'>🎟️ Canjear Licencia</a>"
        "<a href='/app' class='btn ghost'>📱 Entrar con Teléfono</a>"
        "</div></div>"
        "<div class=divider></div>"
        "<div class=stats fade-in>"
        "<div class=stat><div class=number>3</div><div class=label>Búsquedas gratis / 24h</div></div>"
        "<div class=stat><div class=number>∞</div><div class=label>Plan PRO ilimitado</div></div>"
        "<div class=stat><div class=number>⚡</div><div class=label>Instantáneo</div></div>"
        "<div class=stat><div class=number>💬</div><div class=label>Chat Discord</div></div>"
        "</div>"
        "<div class=divider></div>"
        "<section class=fade-in>"
        "<div class=section-title>¿Cómo funciona?</div>"
        "<div class=section-sub>Pasa tu enlace de Google Maps y obtén todo al instante.</div>"
        "<div class=cards>"
        "<div class=card><div class=icon>🔍</div><h3>Busca</h3>"
        "<p>Pega el enlace de Google Maps del negocio. Acepta enlaces cortos y largos.</p></div>"
        "<div class=card><div class=icon>📋</div><h3>Recibe</h3>"
        "<p>Nombre, dirección, Place ID y enlace directo para dejar reseña.</p></div>"
        "<div class=card><div class=icon>⚡</div><h3>Instantáneo</h3>"
        "<p>Resultado en segundos. Se guarda en caché 24h para búsquedas repetidas.</p></div>"
        "</div></section>"
        "<div class=divider></div>"
        "<section class=fade-in>"
        "<div class=section-title>Planes</div>"
        "<div class=cards>"
        "<div class=card><div class=icon>🆓</div><h3>Gratis</h3>"
        "<p>Perfecto para probar. 3 búsquedas cada 24 horas.</p>"
        "<div class=price>0<span> / mes</span></div></div>"
        "<div class=card popular><span class=tag>PRO</span><div class=icon>🚀</div><h3>PRO</h3>"
        "<p>Búsquedas ilimitadas. Chat con soporte. Webhook propio.</p>"
        "<div class=price>Contactar<span> por chat</span></div></div>"
        "</div></section>"
        "<div class=divider></div>"
        "<section class=fade-in>"
        "<h2 class=section-title>Contacto</h2>"
        "<p class=section-sub>Para contratar el plan PRO o cualquier duda.</p>"
        "<a href='https://discord.gg' target=_blank><btn class='btn primary'>💬 Discord — Soporte</btn></a>"
        "<p style='color:#8899aa;margin-top:16px;font-size:14px'>"
        "o contacta directamente por el chat de la web.</p>"
        "</section>"
    )
    return page("PlaceID Bot", body)

async def app_page(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        return web.HTTPFound("/")
    body = (
        "<div class=fade-in>"
        f"<div class=login-box>"
        f"<h3 style='margin-bottom:16px'>{user['first_name']}</h3>"
        f"<p style='color:#8899aa'><code>{user['phone']}</code></p>"
        f"<div style='text-align:center;font-size:32px;font-weight:900;"
        f"background:linear-gradient(135deg,#3b82f6,#8b5cf6);"
        f"-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        f"margin:16px 0'><b id=q>…</b> gratis hoy</div>"
        "</div>"
        "<div class=card><form onsubmit='lookup(event)' style='display:flex;gap:10px'>"
        "<input id=url placeholder='https://maps.app.goo.gl/...' autofocus>"
        "<button type=submit class='btn primary' style='width:auto'>Buscar</button>"
        "</form></div>"
        "<div id=out style='margin-top:16px'></div>"
        "<script>" + JS_APP + "</script>"
        "</div>"
    )
    return page("Panel", body)

async def chat_page(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        return web.HTTPFound("/")
    body = (
        "<div class=fade-in>"
        "<div class=chat-box id=msgs></div>"
        "<form id=frm style='display:flex;gap:10px'>"
        "<textarea id=t rows=1 placeholder='Escribe un mensaje...' style='flex:1'></textarea>"
        "<input type=file id=f accept='image/*'>"
        "<button type=submit class='btn primary' style='width:auto'>Enviar</button>"
        "</form>"
        "<script>" + JS_CHAT + "</script>"
        "</div>"
    )
    return page("Chat", body)

async def redeem_page(_: web.Request) -> web.Response:
    body = (
        "<div class=fade-in>"
        "<div class=login-box>"
        "<h2>Canjear Licencia</h2>"
        "<p>Introduce tu clave y datos para activar.</p>"
        "<input id=k placeholder='Licencia (RBL-...)'>"
        "<div class=row><input id=n placeholder='Nombre'><input id=a placeholder='Apellidos'></div>"
        "<input id=p placeholder='Teléfono'>"
        "<input id=w placeholder='Webhook para resultados (opcional)'>"
        "<button onclick='go()' class='btn primary' style='width:100%;margin-top:8px'>Canjear</button>"
        "<p class=mut id=m></p>"
        "</div>"
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
        "</div>"
    )
    return page("Canjear Licencia", body)

async def account_page(request: web.Request) -> web.Response:
    user = await current_user(request)
    if not user:
        return web.HTTPFound("/")
    wh = user.get("result_webhook") or ""
    body = (
        "<div class=fade-in>"
        "<div class=login-box>"
        f"<h2>{user['first_name']} {user['last_name']}</h2>"
        f"<p style='color:#8899aa'><code>{user['phone']}</code></p>"
        "<div class=divider></div>"
        "<h3 style='margin:20px 0 12px;font-size:18px'>¿Dónde recibes resultados?</h3>"
        "<input id=w placeholder='https://discord.com/api/webhooks/...' value='{wh}'>"
        "<button onclick='save()' class='btn primary' style='width:100%;margin-top:8px'>Guardar</button>"
        "<p class=mut>Vacío = se entregan aquí en la web.</p>"
        "<p class=mut id=m></p>"
        "</div>"
        "<form method=post action='/api/logout' style='margin-top:24px'>"
        "<button type=submit class='btn ghost' style='width:100%'>Cerrar sesión</button></form>"
        "<script>"
        "async function save(){const r=await fetch('/api/settings',"
        "{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({webhook:document.getElementById('w').value})});"
        "const d=await r.json();document.getElementById('m').textContent=d.ok?'✅ Guardado.':'Error';}</script>"
        "</div>"
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
