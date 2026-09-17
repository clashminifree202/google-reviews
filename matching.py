"""Comparacion entre el enlace original y los candidatos de la API.

Puntua nombre, direccion, ciudad, codigo postal y coordenadas.
Si el mejor supera el umbral con margen suficiente se devuelve
directamente; si no, se ofrecen las mejores coincidencias para elegir.
"""
from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from google_places import PlaceCandidate
from maps import MapsInfo

REVIEW_LINK = "https://search.google.com/local/writereview?placeid={place_id}"


def build_review_link(place_id: str) -> str:
    return REVIEW_LINK.format(place_id=place_id)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re_sub(text.lower())
    return " ".join(text.split())


def re_sub(text: str) -> str:
    out = []
    for ch in text:
        out.append(ch if ch.isalnum() else " ")
    return "".join(out)


def name_similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 100.0
    if na in nb or nb in na:
        return 92.0
    return SequenceMatcher(None, na, nb).ratio() * 100.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class ScoredCandidate:
    candidate: PlaceCandidate
    score: float
    reasons: list[str]


def score_candidate(cand: PlaceCandidate, info: MapsInfo) -> ScoredCandidate:
    score = 0.0
    reasons: list[str] = []

    reference = info.name or info.query or ""
    sim = name_similarity(reference, cand.name)
    score += sim * 0.65
    if sim >= 90:
        reasons.append("nombre coincidente")

    if info.query and normalize(info.query) in normalize(cand.formatted_address):
        score += 8.0
        reasons.append("direccion coincidente")

    if cand.city and info.query and normalize(cand.city) in normalize(info.query):
        score += 10.0
        reasons.append("ciudad coincidente")

    if (
        cand.postal_code
        and info.query
        and cand.postal_code in (info.query or "")
    ):
        score += 10.0
        reasons.append("codigo postal coincidente")

    if (
        info.lat is not None
        and info.lng is not None
        and cand.lat is not None
        and cand.lng is not None
    ):
        dist = haversine_km(info.lat, info.lng, cand.lat, cand.lng)
        if dist <= 0.3:
            score += 20.0
            reasons.append("misma ubicacion")
        elif dist <= 2.0:
            score += 8.0
            reasons.append("ubicacion cercana")

    return ScoredCandidate(candidate=cand, score=round(min(score, 100.0), 1), reasons=reasons)


def decide(
    scored: list[ScoredCandidate],
    max_results: int,
    auto_threshold: float = 75.0,
    margin: float = 12.0,
    single_threshold: float = 60.0,
) -> tuple[str, list[ScoredCandidate]]:
    """Devuelve ('auto'|'choose'|'none', candidatos)."""
    ranked = sorted(scored, key=lambda s: s.score, reverse=True)
    if not ranked:
        return "none", []
    top = ranked[: max(1, max_results)]
    best = top[0]
    if len(top) == 1 and best.score >= single_threshold:
        return "auto", [best]
    second = top[1].score if len(top) > 1 else 0.0
    if best.score >= auto_threshold and (best.score - second) >= margin:
        return "auto", [best]
    return "choose", top
