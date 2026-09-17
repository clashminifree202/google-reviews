"""Cache sencilla en SQLite para reutilizar resultados.

Clave: hash SHA-256 de la URL normalizada.
Valor: JSON con los datos del establecimiento.
Sin dependencias externas (sqlite3 de la libreria estandar).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import time
from typing import Any


def normalize_key(url: str) -> str:
    text = url.strip().rstrip("/")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PlaceCache:
    def __init__(self, path: str, ttl: int = 86400) -> None:
        self.path = path
        self.ttl = ttl

    async def init(self) -> None:
        def _init() -> None:
            conn = sqlite3.connect(self.path)
            try:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS place_cache "
                    "(key TEXT PRIMARY KEY, value TEXT NOT NULL, ts INTEGER NOT NULL)"
                )
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_init)

    async def get(self, url: str) -> dict[str, Any] | None:
        key = normalize_key(url)

        def _get() -> dict[str, Any] | None:
            conn = sqlite3.connect(self.path)
            try:
                row = conn.execute(
                    "SELECT value, ts FROM place_cache WHERE key = ?", (key,)
                ).fetchone()
            finally:
                conn.close()
            if not row:
                return None
            value, ts = row
            if time.time() - ts > self.ttl:
                return None
            try:
                data = json.loads(value)
            except (TypeError, ValueError):
                return None
            return data if isinstance(data, dict) else None

        return await asyncio.to_thread(_get)

    async def set(self, url: str, data: dict[str, Any]) -> None:
        key = normalize_key(url)
        payload = json.dumps(data, ensure_ascii=False)

        def _set() -> None:
            conn = sqlite3.connect(self.path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO place_cache (key, value, ts) "
                    "VALUES (?, ?, ?)",
                    (key, payload, int(time.time())),
                )
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_set)

    async def purge_expired(self) -> None:
        cutoff = int(time.time()) - self.ttl

        def _purge() -> None:
            conn = sqlite3.connect(self.path)
            try:
                conn.execute("DELETE FROM place_cache WHERE ts < ?", (cutoff,))
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_purge)
