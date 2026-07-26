from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class CrawlError(RuntimeError):
    pass


class NhaTotClient:
    def __init__(self, base_url: str, user_agent: str, delay: float):
        self.base_url = base_url
        self.user_agent = user_agent
        self.delay = delay
        self._last_request = 0.0

    def listing_page(
        self, category: int, offset: int, limit: int, region: int | None = None
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {
            "cg": category,
            "st": "u",
            "limit": limit,
            "o": offset,
            "w": 1,
        }
        if region:
            params["region_v2"] = region
        return self._get(params)

    def _get(self, params: dict[str, str | int]) -> dict[str, Any]:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        )
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    self._last_request = time.monotonic()
                    payload = json.loads(response.read())
                    if not isinstance(payload, dict) or not isinstance(payload.get("ads"), list):
                        raise CrawlError("API schema changed: missing ads array")
                    return payload
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403, 429):
                    raise CrawlError(f"API stopped crawl with HTTP {exc.code}") from exc
                if attempt == 3:
                    raise CrawlError(f"HTTP {exc.code}") from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                if attempt == 3:
                    raise CrawlError(str(exc)) from exc
            time.sleep(2**attempt)
        raise CrawlError("Request failed")

