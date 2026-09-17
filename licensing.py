"""Licencias, usuarios, cuota gratuita, sesiones y chat web<->Discord.

SQLite + asyncio.to_thread (sin dependencias). Tablas:
  licenses(key, plan, created_at, redeemed_phone, redeemed_at,
           first_name, last_name)
  users(phone, first_name, last_name, session, result_webhook, created_at)
  lookups(id, phone, url, place_id, created_at)
  messages(id, phone, direction, author, text, image, created_at)
"""
from __future__ import annotations

import asyncio
import re
import secrets
import sqlite3
import time
from typing import Any

FREE_DAILY = 3
DAY = 86400


def clean_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if raw and raw.strip().startswith("+"):
        return "+" + digits
    return digits


def valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"\+?\d{6,15}", phone or ""))


def channel_name(phone: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", phone.lower())
    return f"web-{slug}"[:90] or "web-unknown"


def new_key() -> str:
    parts = [secrets.token_hex(2).upper() for _ in range(3)]
    return "RBL-" + "-".join(parts)


class Store:
    def __init__(self, path: str) -> None:
        self.path = path

    async def init(self) -> None:
        def _init() -> None:
            conn = sqlite3.connect(self.path)
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS licenses(
                      key TEXT PRIMARY KEY, plan TEXT NOT NULL,
                      created_at INTEGER NOT NULL,
                      redeemed_phone TEXT, redeemed_at INTEGER,
                      first_name TEXT, last_name TEXT);
                    CREATE TABLE IF NOT EXISTS users(
                      phone TEXT PRIMARY KEY, first_name TEXT NOT NULL,
                      last_name TEXT NOT NULL DEFAULT '',
                      session TEXT, result_webhook TEXT,
                      created_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS lookups(
                      id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT NOT NULL,
                      url TEXT NOT NULL, place_id TEXT NOT NULL,
                      created_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS messages(
                      id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT NOT NULL,
                      direction TEXT NOT NULL, author TEXT NOT NULL DEFAULT '',
                      text TEXT NOT NULL DEFAULT '', image TEXT NOT NULL DEFAULT '',
                      created_at INTEGER NOT NULL);
                    """
                )
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_init)

    def _run(self, fn, *args):
        return asyncio.to_thread(self._sync, fn, *args)

    def _sync(self, fn, *args):
        conn = sqlite3.connect(self.path)
        try:
            conn.row_factory = sqlite3.Row
            out = fn(conn, *args)
            conn.commit()
            return out
        finally:
            conn.close()

    # ---- licencias ----
    async def create_key(self, plan: str = "PRO") -> str:
        def _q(conn):
            for _ in range(5):
                key = new_key()
                if not conn.execute(
                    "SELECT 1 FROM licenses WHERE key=?", (key,)
                ).fetchone():
                    conn.execute(
                        "INSERT INTO licenses(key,plan,created_at) VALUES(?,?,?)",
                        (key, plan, int(time.time())),
                    )
                    return key
            raise RuntimeError("No se pudo generar la clave.")

        return await self._run(_q)

    async def delete_key(self, key: str) -> bool:
        def _q(conn):
            cur = conn.execute("DELETE FROM licenses WHERE key=?", (key.strip().upper(),))
            return cur.rowcount > 0

        return await self._run(_q)

    async def list_keys(self) -> list[dict[str, Any]]:
        def _q(conn):
            rows = conn.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

        return await self._run(_q)

    async def redeem(
        self, key: str, first_name: str, last_name: str, phone: str
    ) -> dict[str, Any]:
        """Canjea una clave. Devuelve dict ok o error."""
        key = key.strip().upper()
        first_name, last_name = first_name.strip(), last_name.strip()
        phone = clean_phone(phone)
        if not key or not first_name or not valid_phone(phone):
            return {"ok": False, "error": "Revisa los datos: nombre y teléfono válido."}

        def _q(conn):
            row = conn.execute("SELECT * FROM licenses WHERE key=?", (key,)).fetchone()
            if not row:
                return {"ok": False, "error": "Esa licencia no existe."}
            if row["redeemed_phone"]:
                return {"ok": False, "error": "Esa licencia ya fue canjeada."}
            now = int(time.time())
            conn.execute(
                "UPDATE licenses SET redeemed_phone=?, redeemed_at=?,"
                " first_name=?, last_name=? WHERE key=?",
                (phone, now, first_name, last_name, key),
            )
            conn.execute(
                "INSERT OR IGNORE INTO users(phone,first_name,last_name,created_at)"
                " VALUES(?,?,?,?)",
                (phone, first_name, last_name, now),
            )
            conn.execute(
                "UPDATE users SET first_name=?, last_name=? WHERE phone=?",
                (first_name, last_name, phone),
            )
            return {
                "ok": True,
                "key": key,
                "plan": row["plan"],
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
            }

        return await self._run(_q)

    async def licensed(self, phone: str) -> bool:
        def _q(conn):
            return bool(
                conn.execute(
                    "SELECT 1 FROM licenses WHERE redeemed_phone=?", (phone,)
                ).fetchone()
            )

        return await self._run(_q)

    # ---- cuota gratuita: 3 cada 24h ----
    async def quota_left(self, phone: str) -> int:
        if await self.licensed(phone):
            return 10**9
        now = int(time.time())

        def _q(conn):
            row = conn.execute(
                "SELECT COUNT(*) c FROM lookups WHERE phone=? AND created_at>?",
                (phone, now - DAY),
            ).fetchone()
            return max(0, FREE_DAILY - int(row["c"]))

        return await self._run(_q)

    async def log_lookup(self, phone: str, url: str, place_id: str) -> None:
        def _q(conn):
            conn.execute(
                "INSERT INTO lookups(phone,url,place_id,created_at) VALUES(?,?,?,?)",
                (phone, url, place_id, int(time.time())),
            )

        await self._run(_q)

    async def history(self, phone: str, limit: int = 20) -> list[dict[str, Any]]:
        def _q(conn):
            rows = conn.execute(
                "SELECT url,place_id,created_at FROM lookups WHERE phone=?"
                " ORDER BY id DESC LIMIT ?",
                (phone, limit),
            ).fetchall()
            return [dict(r) for r in rows]

        return await self._run(_q)

    # ---- usuarios y sesiones ----
    async def get_user(self, phone: str) -> dict[str, Any] | None:
        def _q(conn):
            row = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
            return dict(row) if row else None

        return await self._run(_q)

    async def register(
        self, phone: str, first_name: str, last_name: str = ""
    ) -> dict[str, Any]:
        phone = clean_phone(phone)
        first_name = first_name.strip()
        if not valid_phone(phone) or not first_name:
            return {"ok": False, "error": "Nombre y teléfono válido."}
        token = secrets.token_urlsafe(24)
        now = int(time.time())

        def _q(conn):
            conn.execute(
                "INSERT INTO users(phone,first_name,last_name,session,created_at)"
                " VALUES(?,?,?,?,?) ON CONFLICT(phone) DO UPDATE SET"
                " first_name=excluded.first_name, last_name=excluded.last_name,"
                " session=excluded.session",
                (phone, first_name, last_name.strip(), token, now),
            )
            return {"ok": True, "token": token}

        return await self._run(_q)

    async def login_token(self, phone: str) -> str | None:
        token = secrets.token_urlsafe(24)

        def _q(conn):
            cur = conn.execute(
                "UPDATE users SET session=? WHERE phone=?", (token, phone)
            )
            return token if cur.rowcount else None

        return await self._run(_q)

    async def user_by_session(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None

        def _q(conn):
            row = conn.execute("SELECT * FROM users WHERE session=?", (token,)).fetchone()
            return dict(row) if row else None

        return await self._run(_q)

    async def logout(self, token: str) -> None:
        def _q(conn):
            conn.execute("UPDATE users SET session=NULL WHERE session=?", (token,))

        await self._run(_q)

    async def set_webhook(self, phone: str, url: str) -> None:
        url = (url or "").strip()

        def _q(conn):
            conn.execute(
                "UPDATE users SET result_webhook=? WHERE phone=?", (url or None, phone)
            )

        await self._run(_q)

    # ---- mensajes web<->Discord ----
    async def add_message(
        self, phone: str, direction: str, author: str,
        text: str, image: str = "",
    ) -> int:
        def _q(conn):
            cur = conn.execute(
                "INSERT INTO messages(phone,direction,author,text,image,created_at)"
                " VALUES(?,?,?,?,?,?)",
                (phone, direction, author, text or "", image or "", int(time.time())),
            )
            return cur.lastrowid

        return await self._run(_q)

    async def get_messages(
        self, phone: str, since_id: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        def _q(conn):
            rows = conn.execute(
                "SELECT id,direction,author,text,image,created_at FROM messages"
                " WHERE phone=? AND id>? ORDER BY id ASC LIMIT ?",
                (phone, since_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

        return await self._run(_q)
