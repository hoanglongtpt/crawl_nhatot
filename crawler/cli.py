from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import Settings
from .push import push_file
from .runner import run


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Nhà Tốt public listing crawler")
    commands = root.add_subparsers(dest="command", required=True)
    crawl = commands.add_parser("crawl")
    crawl.add_argument("--days", type=int, default=None)
    crawl.add_argument("--reset", action="store_true")
    push = commands.add_parser("push")
    push.add_argument("--file", required=True, type=Path)
    commands.add_parser("doctor")
    return root


def main() -> int:
    args = parser().parse_args()
    settings = Settings.from_env()
    if args.command == "doctor":
        print(json.dumps({
            "base_url": settings.base_url,
            "days": settings.days,
            "categories": settings.categories,
            "regions": settings.regions or "all",
            "database": str(settings.database_path),
            "import_url": settings.laravel_import_url,
        }, ensure_ascii=False, indent=2))
        return 0
    if args.command == "crawl":
        path = run(settings, days=args.days, reset=args.reset)
        print(f"Exported: {path}")
        return 0
    result = push_file(settings, args.file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

