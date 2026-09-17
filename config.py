"""Configuracion centralizada del bot.

Todas las claves y ajustes se leen de variables de entorno (archivo .env).
Nunca se escriben secretos en el codigo ni se muestran en los logs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_id(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    discord_token: str
    google_api_key: str = ""
    provider: str = "auto"  # api | finder | auto
    cache_ttl: int = 86400
    max_results: int = 5
    auto_threshold: float = 75.0
    score_margin: float = 12.0
    http_timeout: int = 20
    overall_timeout: int = 180
    finder_timeout: int = 60
    cache_path: str = "placeid_cache.db"
    app_db_path: str = "app.db"
    selection_timeout: int = 180
    port: int = 8080
    guild_id: int = 1376191955511410688
    sales_category_id: int = 1390861758880682055
    owner_id: int = 1306929787033354250
    owner_name: str = "Marcos V."
    sales_webhook_url: str = ""
    discord_invite_url: str = ""
    bot_username: str = "web-tlf"


def load_settings() -> Settings:
    """Lee la configuracion y valida lo imprescindible."""
    if not os.getenv("DISCORD_TOKEN"):
        raise RuntimeError(
            "Falta la variable de entorno obligatoria DISCORD_TOKEN. "
            "Copia .env.example a .env y completalo."
        )
    provider = os.getenv("PROVIDER", "auto").strip().lower()
    if provider not in ("api", "finder", "auto"):
        raise RuntimeError("PROVIDER debe ser api, finder o auto.")
    return Settings(
        discord_token=os.getenv("DISCORD_TOKEN", ""),
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        provider=provider,
        cache_ttl=_get_int("CACHE_TTL", 86400),
        max_results=_get_int("MAX_RESULTS", 5),
        auto_threshold=_get_float("AUTO_THRESHOLD", 75.0),
        score_margin=_get_float("SCORE_MARGIN", 12.0),
        http_timeout=_get_int("HTTP_TIMEOUT", 20),
        overall_timeout=_get_int("OVERALL_TIMEOUT", 180),
        finder_timeout=_get_int("FINDER_TIMEOUT", 60),
        cache_path=os.getenv("CACHE_PATH", "placeid_cache.db"),
        app_db_path=os.getenv("APP_DB_PATH", "app.db"),
        selection_timeout=_get_int("SELECTION_TIMEOUT", 180),
        port=_get_int("PORT", 8080),
        guild_id=_get_id("GUILD_ID", 1376191955511410688),
        sales_category_id=_get_id("SALES_CATEGORY_ID", 1390861758880682055),
        owner_id=_get_id("OWNER_ID", 1306929787033354250),
        owner_name=os.getenv("OWNER_NAME", "Marcos V."),
        sales_webhook_url=os.getenv("SALES_WEBHOOK_URL", ""),
        discord_invite_url=os.getenv("DISCORD_INVITE_URL", ""),
        bot_username=os.getenv("BOT_USERNAME", "web-tlf"),
    )


settings = load_settings()
