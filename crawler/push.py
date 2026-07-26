from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from .config import Settings


def push_file(settings: Settings, path: Path, batch_size: int = 50) -> dict:
    if not settings.laravel_token:
        raise RuntimeError("LARAVEL_CRAWLER_TOKEN is empty")
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    totals = {"created": 0, "updated": 0, "failed": 0}
    for start in range(0, len(lines), batch_size):
        body = json.dumps({"items": lines[start : start + batch_size]}).encode("utf-8")
        request = urllib.request.Request(
            settings.laravel_import_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {settings.laravel_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": settings.user_agent,
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read())
            for key in totals:
                totals[key] += int(result.get(key, 0))
    return totals

