"""Cliente de Google Places API (New).

Usa los endpoints actuales recomendados por Google:
  POST https://places.googleapis.com/v1/places:searchText
  GET  https://places.googleapis.com/v1/places/{placeId}

Se solicitan unicamente los campos necesarios (field mask) y los
detalles solo se piden cuando faltan componentes de direccion.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import aiohttp

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

SEARCH_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.addressComponents",
        "places.location",
    ]
)
DETAILS_MASK = ",".join(
    [
        "id",
        "displayName",
        "formattedAddress",
        "addressComponents",
        "location",
    ]
)


class PlacesError(Exception):
    """Error base del modulo."""


class PlacesAuthError(PlacesError):
    """Clave invalida o API no habilitada (sin exponer la clave)."""


class PlacesQuotaError(PlacesError):
    """Cuota agotada o demasiadas peticiones."""


class PlacesRequestError(PlacesError):
    """Peticion rechazada por la API."""


@dataclass
class PlaceCandidate:
    place_id: str
    name: str = ""
    formatted_address: str = ""
    street: str = ""
    city: str = ""
    postal_code: str = ""
    country: str = ""
    lat: float | None = None
    lng: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _component(components: list[dict[str, Any]], wanted: str) -> str:
    for comp in components:
        if wanted in comp.get("types", []):
            return comp.get("longText", "") or comp.get("shortText", "")
    return ""


def parse_place(data: dict[str, Any]) -> PlaceCandidate | None:
    """Convierte la respuesta de la API en un candidato normalizado."""
    place_id = data.get("id", "")
    if not place_id:
        return None
    name = (data.get("displayName") or {}).get("text", "")
    components = data.get("addressComponents", []) or []
    route = _component(components, "route")
    number = _component(components, "street_number")
    street = f"{route} {number}".strip()
    city = _component(components, "locality") or _component(
        components, "administrative_area_level_2"
    )
    location = data.get("location") or {}
    return PlaceCandidate(
        place_id=place_id,
        name=name,
        formatted_address=data.get("formattedAddress", ""),
        street=street,
        city=city,
        postal_code=_component(components, "postal_code"),
        country=_component(components, "country"),
        lat=location.get("latitude"),
        lng=location.get("longitude"),
        raw=data,
    )


def _map_status(status: int) -> PlacesError:
    if status in (401, 403):
        return PlacesAuthError(
            "La API de Google Places no esta disponible "
            "(clave invalida, API no habilitada o clave con restricciones). "
            "Revisa la clave en Google Cloud o usa PROVIDER=finder "
            "para no necesitar clave."
        )
    if status == 429:
        return PlacesQuotaError(
            "Se ha superado la cuota de la API. Intentalo mas tarde."
        )
    return PlacesRequestError(f"La API ha devuelto un error (HTTP {status}).")


async def search_text(
    session: aiohttp.ClientSession,
    api_key: str,
    query: str,
    *,
    language: str = "es",
    max_results: int = 5,
    lat: float | None = None,
    lng: float | None = None,
    timeout: int = 20,
) -> list[PlaceCandidate]:
    """Busca establecimientos por texto. Una sola peticion."""
    body: dict[str, Any] = {
        "textQuery": query,
        "languageCode": language,
        "maxResultCount": max(1, min(max_results, 20)),
    }
    if lat is not None and lng is not None:
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 5000.0,
            }
        }
    try:
        async with session.post(
            SEARCH_URL,
            json=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": SEARCH_MASK,
            },
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status != 200:
                raise _map_status(resp.status)
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise PlacesError(
            "La búsqueda ha tardado demasiado. Inténtalo de nuevo."
        ) from exc
    results = []
    for item in data.get("places", []) or []:
        cand = parse_place(item)
        if cand:
            results.append(cand)
    return results


async def get_details(
    session: aiohttp.ClientSession,
    api_key: str,
    place_id: str,
    timeout: int = 20,
) -> PlaceCandidate | None:
    """Obtiene los datos completos de un lugar. Solo si hacen falta."""
    try:
        async with session.get(
            DETAILS_URL.format(place_id=place_id),
            headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": DETAILS_MASK,
            },
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status != 200:
                raise _map_status(resp.status)
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise PlacesError(
            "La búsqueda ha tardado demasiado. Inténtalo de nuevo."
        ) from exc
    return parse_place(data)


def needs_details(cand: PlaceCandidate) -> bool:
    """True si faltan ciudad o codigo postal (motivo para pedir detalles)."""
    return not cand.city or not cand.postal_code
