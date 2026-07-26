from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .client import NhaTotClient
from .config import Settings
from .normalize import normalize_ad
from .storage import Storage


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def run(settings: Settings, days: int | None = None, reset: bool = False) -> Path:
    days = days or settings.days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    export_path = settings.export_dir / datetime.now().strftime("nhatot_%Y%m%d_%H%M%S.jsonl")
    storage = Storage(settings.database_path)
    run_id = storage.start_run(iso_now(), cutoff.isoformat())
    client = NhaTotClient(settings.base_url, settings.user_agent, settings.request_delay)
    received = accepted = 0
    error: str | None = None

    try:
        with export_path.open("w", encoding="utf-8") as output:
            regions: tuple[int | None, ...] = settings.regions or (None,)
            for category in settings.categories:
                for region in regions:
                    key = f"{category}:{region or 'all'}"
                    offset = 0 if reset else storage.checkpoint(key)
                    old_pages = 0
                    for _ in range(settings.max_pages):
                        payload = client.listing_page(category, offset, settings.limit, region)
                        ads = payload["ads"]
                        if not ads:
                            storage.save_checkpoint(key, offset, "completed", iso_now())
                            break
                        page_has_recent = False
                        for ad in ads:
                            received += 1
                            item = normalize_ad(ad, iso_now())
                            published = parse_iso(item["published_at"])
                            if published and published >= cutoff and item["source_listing_id"]:
                                page_has_recent = True
                                accepted += 1
                                storage.upsert(item)
                                output.write(json.dumps(item, ensure_ascii=False) + "\n")
                        old_pages = 0 if page_has_recent else old_pages + 1
                        offset += len(ads)
                        storage.save_checkpoint(key, offset, "running", iso_now())
                        if old_pages >= settings.old_page_stop:
                            storage.save_checkpoint(key, offset, "completed", iso_now())
                            break
    except Exception as exc:
        error = str(exc)
        storage.finish_run(run_id, iso_now(), "failed", received, accepted, error)
        raise
    else:
        storage.finish_run(run_id, iso_now(), "completed", received, accepted)
    finally:
        storage.close()

    return export_path

