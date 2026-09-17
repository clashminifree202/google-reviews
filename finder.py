"""Proveedor sin clave API: la pagina oficial del Place ID Finder.

Abre la pagina de ejemplo de Google en un Chromium headless y ejecuta
su propia libreria oficial Maps JavaScript Places (`Place.searchByText`),
exactamente el mismo mecanismo que el finder manual: se busca el texto
y se lee el identificador. Todo ocurre dentro del navegador, como si el
usuario usara la pagina; no se necesita ni se reutiliza ninguna clave.

Requiere: pip install playwright  +  playwright install chromium
"""
from __future__ import annotations

import asyncio
from typing import Any

FINDER_URL = (
    "https://maps-docs-team.web.app/samples/places-placeid-finder/dist/"
)

_SEARCH_JS = """async (args) => {
  const {Place} = await google.maps.importLibrary('places');
  const req = {textQuery: args.query,
               fields: ['id', 'displayName', 'formattedAddress',
                        'addressComponents', 'location']};
  const {places} = await Place.searchByText(req);
  return (places || []).slice(0, args.maxResults).map(p => ({
    id: p.id || '',
    displayName: p.displayName ? {text: p.displayName} : null,
    formattedAddress: p.formattedAddress || '',
    addressComponents: (p.addressComponents || []).map(c => ({
      longText: c.longText || '', shortText: c.shortText || '',
      types: c.types || []})),
    location: p.location
      ? {latitude: p.location.lat(), longitude: p.location.lng()} : null,
  }));
}"""


class FinderError(Exception):
    """Error base del proveedor finder."""


class FinderUnavailableError(FinderError):
    """Playwright o Chromium no estan instalados."""


class FinderTimeoutError(FinderError):
    """La busqueda en el finder tardo demasiado."""


class Finder:
    def __init__(self, url: str = FINDER_URL, timeout: int = 60) -> None:
        self.url = url
        self.timeout = timeout
        self._pw = None
        self._browser = None
        self._page = None
        self._lock = asyncio.Lock()

    async def _ensure_page(self):
        if self._page is not None and not self._page.is_closed():
            return self._page
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise FinderUnavailableError(
                "El proveedor 'finder' necesita Playwright: "
                "pip install playwright y playwright install chromium."
            ) from exc
        try:
            if self._pw is None:
                self._pw = await async_playwright().start()
            if self._browser is None or not self._browser.is_connected():
                self._browser = await self._pw.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--enable-unsafe-swiftshader",
                    ],
                )
            self._page = await self._browser.new_page()
            await self._page.goto(
                self.url, wait_until="domcontentloaded", timeout=45000
            )
            await self._page.wait_for_function(
                "() => !!(window.google && google.maps && google.maps.importLibrary)",
                timeout=45000,
            )
        except FinderUnavailableError:
            raise
        except Exception as exc:
            await self._reset()
            raise FinderUnavailableError(
                "No se pudo iniciar el navegador del finder: "
                f"{exc}. Comprueba 'playwright install chromium'."
            ) from exc
        return self._page

    async def _reset(self) -> None:
        page, browser, pw = self._page, self._browser, self._pw
        self._page = self._browser = self._pw = None
        for obj, meth in ((page, "close"), (browser, "close"), (pw, "stop")):
            if obj is not None:
                try:
                    await getattr(obj, meth)()
                except Exception:
                    pass

    async def search(
        self, query: str, max_results: int = 5
    ) -> list[dict[str, Any]]:
        """Busca en el finder y devuelve lugares en formato Places API."""
        query = (query or "").strip()
        if not query:
            raise FinderError("Consulta vacía para el finder.")
        async with self._lock:
            for attempt in (1, 2):
                page = await self._ensure_page()
                try:
                    result = await asyncio.wait_for(
                        page.evaluate(
                            _SEARCH_JS,
                            {"query": query, "maxResults": max_results},
                        ),
                        timeout=self.timeout,
                    )
                    places = result if isinstance(result, list) else []
                    return [p for p in places if isinstance(p, dict) and p.get("id")]
                except FinderUnavailableError:
                    raise
                except (asyncio.TimeoutError, TimeoutError) as exc:
                    await self._reset()
                    if attempt == 2:
                        raise FinderTimeoutError(
                            "La búsqueda ha tardado demasiado. "
                            "Inténtalo de nuevo."
                        ) from exc
                except Exception:
                    await self._reset()
                    if attempt == 2:
                        raise FinderError(
                            "No se ha encontrado ningún establecimiento "
                            "que coincida con la información proporcionada."
                        )
        return []

    async def close(self) -> None:
        async with self._lock:
            await self._reset()


finder = Finder()
