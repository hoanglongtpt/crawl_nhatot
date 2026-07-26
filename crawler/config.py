from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path | None = None) -> None:
    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def csv_ints(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    base_url: str
    days: int
    limit: int
    request_delay: float
    max_pages: int
    old_page_stop: int
    categories: tuple[int, ...]
    regions: tuple[int, ...]
    user_agent: str
    database_path: Path
    export_dir: Path
    laravel_import_url: str
    laravel_token: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_env()
        return cls(
            base_url=os.getenv(
                "NHATOT_BASE_URL",
                "https://gateway.chotot.com/v1/public/ad-listing",
            ),
            days=int(os.getenv("NHATOT_DAYS", "7")),
            limit=max(1, min(int(os.getenv("NHATOT_LIMIT", "20")), 100)),
            request_delay=max(0.5, float(os.getenv("NHATOT_REQUEST_DELAY", "1.0"))),
            max_pages=max(1, int(os.getenv("NHATOT_MAX_PAGES_PER_PARTITION", "500"))),
            old_page_stop=max(1, int(os.getenv("NHATOT_OLD_PAGE_STOP", "3"))),
            categories=csv_ints(os.getenv("NHATOT_CATEGORIES", "1010,1020,1040,1050")),
            regions=csv_ints(os.getenv("NHATOT_REGIONS", "")),
            user_agent=os.getenv("NHATOT_USER_AGENT", "CloneNhaTotResearchBot/1.0"),
            database_path=ROOT / "data" / "crawler.sqlite3",
            export_dir=ROOT / "exports",
            laravel_import_url=os.getenv(
                "LARAVEL_IMPORT_URL",
                "http://clone_nhatot.test/api/crawler/import",
            ),
            laravel_token=os.getenv("LARAVEL_CRAWLER_TOKEN", ""),
        )

