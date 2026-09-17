"""Bot de Discord: enlace de Google Maps -> Place ID + enlace de resena.

Uso: /placeid url:<enlace de Google Maps>
"""
from __future__ import annotations

import asyncio
import io
import logging
import secrets
import time
from typing import Any

import aiohttp
import discord
from discord import app_commands

from cache import PlaceCache
from config import settings
from finder import FinderError, finder
from google_places import (
    PlaceCandidate,
    PlacesError,
    get_details,
    needs_details,
    parse_place,
    search_text,
)
from licensing import Store, channel_name
from maps import (
    InvalidMapsUrlError,
    MapsInfo,
    UnresolvableUrlError,
    is_maps_url,
    is_short_url,
    parse_maps_url,
    resolve_url,
)
from matching import build_review_link, decide, score_candidate

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger("placeid-bot")

SEP = "━" * 28

intents = discord.Intents.default()
intents.message_content = True  # necesario para ,genkey y ,delkey
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

session: aiohttp.ClientSession | None = None
cache = PlaceCache(settings.cache_path, settings.cache_ttl)
store = Store(settings.app_db_path)

# Selecciones pendientes: token -> {user_id, options, expires}
pending: dict[str, dict[str, Any]] = {}


def result_to_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": data.get("name", ""),
        "address": data.get("address", ""),
        "city": data.get("city", ""),
        "postal_code": data.get("postal_code", ""),
        "place_id": data.get("place_id", ""),
        "review_url": data.get("review_url", ""),
    }


def candidate_payload(cand: PlaceCandidate) -> dict[str, Any]:
    review_url = build_review_link(cand.place_id)
    return result_to_dict(
        {
            "name": cand.name,
            "address": cand.formatted_address,
            "city": cand.city,
            "postal_code": cand.postal_code,
            "place_id": cand.place_id,
            "review_url": review_url,
        }
    )


def result_embed(data: dict[str, Any], cached: bool = False) -> discord.Embed:
    description = (
        f"{SEP}\nGOOGLE PLACE ID\n{SEP}\n\n"
        f"**Establecimiento**\n{data.get('name') or '-'}\n\n"
        f"**Dirección**\n{data.get('address') or '-'}\n\n"
        f"**Ciudad**\n{data.get('city') or '-'}\n\n"
        f"**Código postal**\n{data.get('postal_code') or '-'}\n\n"
        f"**Place ID**\n`{data.get('place_id')}`\n\n"
        f"**ENLACE DE RESEÑA**\n`{data.get('review_url')}`"
    )
    embed = discord.Embed(description=description, colour=0x1A73E8)
    if cached:
        embed.set_footer(text="Resultado recuperado de la caché")
    return embed


def review_view(review_url: str) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(
            label="Abrir reseña",
            style=discord.ButtonStyle.link,
            url=review_url,
        )
    )
    return view


class CandidateView(discord.ui.View):
    def __init__(self, token: str, count: int) -> None:
        super().__init__(timeout=settings.selection_timeout)
        self.token = token
        for i in range(count):
            btn = discord.ui.Button(
                label=str(i + 1),
                style=discord.ButtonStyle.primary,
                custom_id=f"pick:{token}:{i}",
            )
            btn.callback = self._make_pick(i)
            self.add_item(btn)
        cancel = discord.ui.Button(
            label="Cancelar",
            style=discord.ButtonStyle.secondary,
            custom_id=f"cancel:{token}",
        )
        cancel.callback = self._cancel
        self.add_item(cancel)

    def _make_pick(self, index: int):
        async def _cb(interaction: discord.Interaction) -> None:
            await on_pick(interaction, self.token, index)

        return _cb

    async def _cancel(self, interaction: discord.Interaction) -> None:
        entry = pending.pop(self.token, None)
        if entry and interaction.user.id != entry["user_id"]:
            await interaction.response.send_message(
                "Esta selección pertenece a otro usuario.", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content="Selección cancelada.", embed=None, view=None
        )

    async def on_timeout(self) -> None:
        pending.pop(self.token, None)


def candidates_text(options: list[dict[str, Any]]) -> str:
    lines = [SEP, "POSIBLES COINCIDENCIAS", SEP, ""]
    for i, opt in enumerate(options, start=1):
        lines.append(f"**{i}. {opt.get('name') or '-'}**")
        lines.append(f"{opt.get('address') or '-'}")
        if opt.get("city") or opt.get("postal_code"):
            lines.append(
                f"{opt.get('postal_code', '')} {opt.get('city', '')}".strip()
            )
        lines.append("")
        lines.append("Place ID:")
        lines.append(f"`{opt.get('place_id')}`")
        lines.append("")
    lines.append("Selecciona una opción:")
    lines.append("`" + "` / `".join(str(i + 1) for i in range(len(options))) + "`")
    return "\n".join(lines)


async def on_pick(
    interaction: discord.Interaction, token: str, index: int
) -> None:
    entry = pending.get(token)
    if not entry:
        await interaction.response.send_message(
            "Esta selección ha caducado. Vuelve a usar /placeid.",
            ephemeral=True,
        )
        return
    if interaction.user.id != entry["user_id"]:
        await interaction.response.send_message(
            "Esta selección pertenece a otro usuario.", ephemeral=True
        )
        return
    options: list[dict[str, Any]] = entry["options"]
    if index >= len(options):
        await interaction.response.send_message(
            "Opción no válida.", ephemeral=True
        )
        return
    data = options[index]
    pending.pop(token, None)
    log.info("Usuario: %s | Selección: %s", interaction.user.id, data["place_id"])
    await cache.set(entry["cache_key"], result_to_dict(data))
    await interaction.response.edit_message(
        content=None,
        embed=result_embed(data),
        view=review_view(data["review_url"]),
    )


async def enrich_if_needed(cand: PlaceCandidate) -> PlaceCandidate:
    # El finder ya trae todos los campos; los detalles solo son para la API.
    if active_provider() != "api":
        return cand
    if needs_details(cand) and session is not None:
        full = await get_details(
            session, settings.google_api_key, cand.place_id,
            timeout=settings.http_timeout,
        )
        if full:
            return full
    return cand


def active_provider() -> str:
    if settings.provider == "auto":
        return "api" if settings.google_api_key else "finder"
    return settings.provider


async def lookup_candidates(
    reference: str, info: MapsInfo
) -> list[PlaceCandidate]:
    """Busca candidatos con el proveedor configurado (api o finder)."""
    assert session is not None
    if active_provider() == "api":
        if not settings.google_api_key:
            raise PlacesError(
                "PROVIDER=api pero falta GOOGLE_API_KEY en la configuración."
            )
        return await search_text(
            session,
            settings.google_api_key,
            reference,
            max_results=settings.max_results,
            lat=info.lat,
            lng=info.lng,
            timeout=settings.http_timeout,
        )
    raw = await finder.search(reference, max_results=settings.max_results)
    candidates = []
    for item in raw:
        cand = parse_place(item)
        if cand:
            candidates.append(cand)
    return candidates


async def run_lookup(url: str, user_id: int) -> dict[str, Any]:
    """Flujo completo. Devuelve dict con 'kind' y datos para responder."""
    log.info("Usuario: %s | URL recibida: %s", user_id, url)
    if not is_maps_url(url):
        return {
            "kind": "error",
            "message": "La URL proporcionada no parece ser un enlace válido de Google Maps.",
        }

    cached = await cache.get(url)
    if cached and cached.get("place_id"):
        log.info("Place ID obtenido (caché)")
        return {"kind": "result", "data": cached, "cached": True}

    assert session is not None
    final_url = url
    if is_short_url(url):
        log.info("Resolviendo URL...")
        try:
            final_url = await resolve_url(
                session, url, timeout=settings.http_timeout
            )
        except UnresolvableUrlError as exc:
            return {"kind": "error", "message": str(exc)}
        if not is_maps_url(final_url):
            return {
                "kind": "error",
                "message": "No se ha podido resolver el enlace de Google Maps.",
            }

    info: MapsInfo = parse_maps_url(final_url, original_url=url)
    reference = info.name or info.query
    if not reference:
        return {
            "kind": "error",
            "message": "No se ha encontrado ningún establecimiento "
            "que coincida con la información proporcionada. "
            "Usa un enlace que incluya el nombre del establecimiento.",
        }
    log.info("Establecimiento encontrado: %s", reference)

    try:
        candidates = await lookup_candidates(reference, info)
    except (PlacesError, FinderError) as exc:
        return {"kind": "error", "message": str(exc)}

    if not candidates:
        return {
            "kind": "error",
            "message": "No se ha encontrado ningún establecimiento "
            "que coincida con la información proporcionada.",
        }

    scored = [score_candidate(c, info) for c in candidates]
    decision, top = decide(
        scored,
        settings.max_results,
        auto_threshold=settings.auto_threshold,
        margin=settings.score_margin,
    )
    if decision == "auto":
        cand = await enrich_if_needed(top[0].candidate)
        data = candidate_payload(cand)
        await cache.set(url, result_to_dict(data))
        log.info("Place ID obtenido")
        log.info("Enlace generado")
        return {"kind": "result", "data": data, "cached": False}

    options: list[dict[str, Any]] = []
    for s in top:
        cand = await enrich_if_needed(s.candidate)
        options.append(candidate_payload(cand))
    return {"kind": "choose", "options": options}


@app_commands.command(name="placeid", description="Obtiene el Place ID y el enlace de reseña desde un enlace de Google Maps")
@app_commands.describe(url="Enlace de Google Maps (corto o largo)")
async def placeid(interaction: discord.Interaction, url: str) -> None:
    await interaction.response.defer()
    try:
        outcome = await asyncio.wait_for(
            run_lookup(url.strip(), interaction.user.id),
            timeout=settings.overall_timeout,
        )
    except asyncio.TimeoutError:
        await interaction.followup.send(
            "La búsqueda ha tardado demasiado. Inténtalo de nuevo."
        )
        return
    except InvalidMapsUrlError:
        await interaction.followup.send(
            "La URL proporcionada no parece ser un enlace válido de Google Maps."
        )
        return
    except Exception:  # noqa: BLE001 - respuesta generica, detalle en logs
        log.exception("Error inesperado procesando la URL")
        await interaction.followup.send(
            "Ha ocurrido un error interno. Inténtalo de nuevo más tarde."
        )
        return

    if outcome["kind"] == "error":
        await interaction.followup.send(outcome["message"])
        return
    if outcome["kind"] == "result":
        data = outcome["data"]
        await interaction.followup.send(
            embed=result_embed(data, cached=outcome.get("cached", False)),
            view=review_view(data["review_url"]),
        )
        return
    # Varias coincidencias: botones de seleccion.
    options: list[dict[str, Any]] = outcome["options"]
    token = secrets.token_urlsafe(8)
    pending[token] = {
        "user_id": interaction.user.id,
        "options": options,
        "cache_key": url.strip(),
        "expires": time.time() + settings.selection_timeout,
    }
    await interaction.followup.send(
        candidates_text(options),
        view=CandidateView(token, len(options)),
    )


@bot.event
async def on_ready() -> None:
    log.info("Bot iniciado")


def is_owner(user: discord.abc.User) -> bool:
    return bool(settings.owner_id) and user.id == settings.owner_id


def display_name(user: discord.abc.User) -> str:
    if is_owner(user):
        return settings.owner_name
    return getattr(user, "display_name", str(user))

def bot_display_name(phone: str, first_name: str = "", last_name: str = "") -> str:
    who = f"{first_name} {last_name}".strip() or "Usuario"
    return f"{settings.bot_username}-{who}"


def sales_guild() -> discord.Guild | None:
    if not settings.guild_id:
        return None
    return bot.get_guild(settings.guild_id)


async def sales_category(guild: discord.Guild):
    if not settings.sales_category_id:
        return None
    return guild.get_channel(settings.sales_category_id)


async def find_user_channel(phone: str):
    guild = sales_guild()
    if guild is None:
        return None
    want = channel_name(phone)
    for ch in guild.text_channels:
        if ch.name == want:
            return ch
    return None


async def ensure_user_channel(
    phone: str, first_name: str = "", last_name: str = ""
):
    """Crea (o reutiliza) web-<tlf> en la categoria y publica la ficha."""
    guild = sales_guild()
    if guild is None:
        raise RuntimeError("Servidor de ventas no configurado.")
    existing = await find_user_channel(phone)
    if existing is not None:
        return existing
    category = await sales_category(guild)
    channel = await guild.create_text_channel(
        channel_name(phone),
        category=category,
        topic=f"web-tlf-{phone}",
    )
    who = f"{first_name} {last_name}".strip() or "Usuario web"
    await channel.send(
        f"{SEP}\nNUEVO CONTACTO WEB\n{SEP}\n\n"
        f"**Nombre**\n{who}\n\n**Teléfono**\n`{phone}`"
    )
    log.info("Canal creado: %s", channel.name)
    return channel


async def post_sales_webhook(dossier: dict[str, Any]) -> None:
    """Envia la ficha de canje al webhook de ventas, si esta configurado."""
    url = settings.sales_webhook_url
    if not url or session is None:
        return
    text = (
        "**Nueva licencia canjeada**\n"
        f"Nombre: {dossier.get('first_name', '')} {dossier.get('last_name', '')}\n"
        f"Teléfono: `{dossier.get('phone', '')}`\n"
        f"Licencia: `{dossier.get('key', '')}`\n"
        f"Plan: {dossier.get('plan', '')}"
    )
    try:
        async with session.post(
            url,
            json={"content": text[:1900]},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status not in (200, 204):
                log.info("Webhook ventas HTTP %s", resp.status)
    except Exception as exc:  # noqa: BLE001
        log.info("Webhook ventas falló: %s", type(exc).__name__)


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    text = (message.content or "").strip()

    # --- comandos del propietario ---
    if text.startswith(",genkey") or text.startswith(",delkey"):
        if not is_owner(message.author):
            return
        if text.startswith(",genkey"):
            parts = text.split()
            plan = parts[1].upper() if len(parts) > 1 else "PRO"
            try:
                key = await store.create_key(plan)
            except Exception:
                await message.channel.send("No se pudo generar la clave.")
                return
            await message.channel.send(
                f"Licencia `{plan}` generada:\n`{key}`"
            )
            log.info("Licencia generada: plan %s", plan)
            return
        # ,delkey
        parts = text.split()
        if len(parts) > 1:
            ok = await store.delete_key(parts[1])
            await message.channel.send(
                "Licencia eliminada." if ok else "Esa licencia no existe."
            )
            return
        rows = await store.list_keys()
        if not rows:
            await message.channel.send("No hay licencias.")
            return
        lines = ["**LICENCIAS**", ""]
        for r in rows[:25]:
            holder = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
            holder = holder or "sin canjear"
            tlf = r.get("redeemed_phone") or "-"
            lines.append(
                f"`{r['key']}` · {r['plan']} · {holder} · `{tlf}`"
            )
        if len(rows) > 25:
            lines.append(f"... y {len(rows) - 25} más.")
        await message.channel.send("\n".join(lines)[:1900])
        return

    # --- relay web<->Discord en canales web-<tlf> ---
    channel = message.channel
    if (
        isinstance(channel, discord.TextChannel)
        and channel.name.startswith("web-")
        and (channel.category is None
             or channel.category.id == settings.sales_category_id
             or not settings.sales_category_id)
    ):
        phone = channel.name[4:] or None
        if not phone:
            return
        author = display_name(message.author)
        body = text
        image = ""
        for att in message.attachments:
            ctype = (att.content_type or "")
            if ctype.startswith("image/") or att.filename.lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".webp")
            ):
                image = att.url
                break
        if not body and not image:
            return
        await store.add_message(phone, "in", author, body, image)
        log.info("Chat %s <- %s", channel.name, bot_display_name(phone))


async def send_to_user(
    phone: str, text: str = "", image_bytes: bytes | None = None,
    filename: str = "foto.jpg", author_name: str = "",
) -> bool:
    """Publica un mensaje (y opcionalmente foto) en el canal del usuario."""
    channel = await find_user_channel(phone)
    if channel is None:
        channel = await ensure_user_channel(phone)
    try:
        if image_bytes:
            await channel.send(
                content=text or None,
                file=discord.File(fp=io.BytesIO(image_bytes),
                                  filename=filename),
            )
        else:
            await channel.send(text or "(sin texto)")
        await store.add_message(phone, "out", author_name or settings.bot_username, text)
        return True
    except Exception as exc:
        log.info("No se pudo enviar al canal: %s", type(exc).__name__)
        return False


async def setup_hook() -> None:
    global session
    session = aiohttp.ClientSession()
    finder.timeout = settings.finder_timeout
    log.info(
        "Proveedor configurado: %s | efectivo: %s | API key: %s",
        settings.provider,
        active_provider(),
        "sí" if settings.google_api_key else "no",
    )
    await cache.init()
    await cache.purge_expired()
    await store.init()
    from web import start_web

    await start_web()
    tree.add_command(placeid)
    await tree.sync()


async def close_session() -> None:
    global session
    try:
        from web import stop_web

        await stop_web()
    except Exception:
        pass
    if session is not None:
        await session.close()
        session = None
    try:
        await finder.close()
    except Exception:
        pass


bot.setup_hook = setup_hook


def main() -> None:
    log.info("Bot iniciado")
    try:
        bot.run(settings.discord_token)
    finally:
        if session is not None:
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.run_until_complete(close_session())
            except RuntimeError:
                pass


if __name__ == "__main__":
    main()
