"""Resolucion y analisis de enlaces de Google Maps.

Acepta enlaces cortos (maps.app.goo.gl) y enlaces largos
(google.com/maps, maps.google.com, etc.), sigue las redirecciones
y extrae nombre, consulta y coordenadas cuando estan disponibles.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import aiohttp
SHORT_HOSTS = {"maps.app.goo.gl"}

# Dominios validos de Google Maps (cualquier TLD de google).
_MAPS_PATH_RE = re.compile(r"^/maps")
_COORD_AT_RE = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
_COORD_DATA_RE = re.compile(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)")
_PLACE_RE = re.compile(r"/maps/place/([^/?#]+)")
_SEARCH_RE = re.compile(r"/maps/search/([^?#]+)")
_COORD_SLUG_RE = re.compile(r"^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$")

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


class MapsError(Exception):
    """Error base del modulo."""


class InvalidMapsUrlError(MapsError):
    """La URL no es un enlace valido de Google Maps."""


class UnresolvableUrlError(MapsError):
    """No se pudo resolver el enlace (red o URL caida)."""


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def is_maps_url(url: str) -> bool:
    """Comprueba que la URL sea http(s) y pertenezca a Google Maps."""
    try:
        parts = urlparse(url.strip())
    except ValueError:
        return False
    if parts.scheme not in ("http", "https"):
        return False
    host = (parts.hostname or "").lower()
    if host in SHORT_HOSTS:
        return True
    if host == "maps.google.com" or host.endswith(".maps.google.com"):
        return True
    # google.<tld>/maps...  (com, es, fr, ...)
    if re.fullmatch(r"(www\.)?google\.[a-z.]+", host or "") and _MAPS_PATH_RE.match(parts.path or ""):
        return True
    return False


def is_short_url(url: str) -> bool:
    return _host(url) in SHORT_HOSTS


@dataclass
class MapsInfo:
    original_url: str
    final_url: str
    name: str | None = None
    query: str | None = None
    lat: float | None = None
    lng: float | None = None


async def resolve_url(session: aiohttp.ClientSession, url: str, timeout: int = 20) -> str:
    """Sigue las redirecciones y devuelve la URL final.

    Si Google interpone la pagina de consentimiento
    (consent.google.com), extrae la URL real del parametro
    'continue' en lugar de fallar.
    """
    try:
        final = await _get_final(session, url, timeout)
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise UnresolvableUrlError(
            "No se ha podido resolver el enlace de Google Maps."
        ) from exc
    unwrapped = _unwrap_consent(final)
    if unwrapped:
        # Un intento mas por si la URL directa ya no pide consentimiento;
        # si falla o vuelve al consentimiento, vale la URL extraida.
        try:
            final2 = await _get_final(session, unwrapped, timeout)
            return _unwrap_consent(final2) or final2
        except (aiohttp.ClientError, asyncio.TimeoutError, UnresolvableUrlError):
            return unwrapped
    return final


async def _get_final(
    session: aiohttp.ClientSession, url: str, timeout: int
) -> str:
    async with session.get(
        url,
        allow_redirects=True,
        max_redirects=10,
        timeout=aiohttp.ClientTimeout(total=timeout),
        headers={"User-Agent": _USER_AGENT},
    ) as resp:
        if resp.status >= 400:
            raise UnresolvableUrlError(
                "No se ha podido resolver el enlace de Google Maps."
            )
        return str(resp.url)


def _unwrap_consent(url: str) -> str | None:
    """Extrae la URL real de una pagina intermedia de consentimiento."""
    host = (urlparse(url).hostname or "").lower()
    if host != "consent.google.com" and not host.startswith("consent."):
        return None
    m = re.search(r"[?&]continue=([^&]+)", url)
    if not m:
        return None
    # unquote (no plus): los '+' de la URL de Maps deben conservarse.
    return unquote(m.group(1))


def _clean_slug(slug: str) -> str | None:
    text = unquote(slug).replace("+", " ").strip()
    if not text or _COORD_SLUG_RE.match(text.replace(" ", "")):
        return None
    return text


def parse_maps_url(url: str, original_url: str = "") -> MapsInfo:
    """Extrae nombre, consulta y coordenadas de una URL de Maps."""
    info = MapsInfo(original_url=original_url or url, final_url=url)

    m = _PLACE_RE.search(url)
    if m:
        info.name = _clean_slug(m.group(1))

    m = _SEARCH_RE.search(url)
    if m:
        info.query = _clean_slug(m.group(1).split("/")[0])

    if not info.query:
        # ?q=... o ?query=... en algunos formatos
        parsed = urlparse(url)
        for key in ("q", "query"):
            vals = [
                v
                for part in parsed.query.split("&")
                for k, _, v in [part.partition("=")]
                if k == key and v
            ]
            if vals:
                info.query = _clean_slug(vals[0])
                break

    m = _COORD_AT_RE.search(url)
    if m:
        info.lat, info.lng = float(m.group(1)), float(m.group(2))
    else:
        m = _COORD_DATA_RE.search(url)
        if m:
            info.lat, info.lng = float(m.group(1)), float(m.group(2))

    return info
