from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){8,10}(?!\d)")


def milliseconds_to_iso(value: Any) -> str | None:
    try:
        timestamp = int(value) / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def normalize_phone(value: Any) -> str | None:
    if not isinstance(value, str) or "*" in value:
        return None
    match = PHONE_RE.search(value)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))
    if digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 11 else None


def public_phone(ad: dict[str, Any]) -> tuple[str | None, str]:
    for key in ("phone", "phone_number", "contact_phone", "mobile"):
        phone = normalize_phone(ad.get(key))
        if phone:
            return phone, "available"
    return None, "masked" if any("*" in str(ad.get(k, "")) for k in ad if "phone" in k) else "unavailable"


def normalize_ad(ad: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    phone, phone_status = public_phone(ad)
    published_at = milliseconds_to_iso(ad.get("orig_list_time") or ad.get("list_time"))
    refreshed_at = milliseconds_to_iso(ad.get("list_time"))
    payload_hash = hashlib.sha256(
        json.dumps(ad, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    list_id = str(ad.get("list_id") or "")
    slug_type = {
        1010: "thue-can-ho-chung-cu",
        1020: "thue-nha-dat",
        1040: "thue-van-phong-mat-bang-kinh-doanh",
        1050: "thue-phong-tro",
    }.get(ad.get("category"), "thue-bat-dong-san")
    return {
        "source_listing_id": list_id,
        "source_ad_id": str(ad.get("ad_id") or ""),
        "source_platform": "nhatot",
        "source_type": "tool_crawl",
        "transaction_type": "rent",
        "source_url": f"https://www.nhatot.com/{slug_type}/{list_id}.htm",
        "category_code": ad.get("category"),
        "category_name": ad.get("category_name"),
        "title": ad.get("subject") or "",
        "description": ad.get("body") or "",
        "price": ad.get("price"),
        "area": ad.get("size"),
        "living_area": ad.get("living_size"),
        "width": ad.get("width"),
        "length": ad.get("length"),
        "bedrooms": ad.get("rooms"),
        "bathrooms": ad.get("toilets"),
        "floors": ad.get("floors"),
        "house_type": ad.get("house_type"),
        "furnishing_type": ad.get("furnishing_sell"),
        "legal_document": ad.get("property_legal_document"),
        "province_source_id": ad.get("region_v2"),
        "province_name": ad.get("region_name_v3") or ad.get("region_name"),
        "district_source_id": ad.get("area_v2"),
        "district_name": ad.get("area_name"),
        "ward_source_id": ad.get("ward"),
        "ward_name": ad.get("ward_name_v3") or ad.get("ward_name"),
        "street_name": ad.get("street_name"),
        "street_number": ad.get("street_number"),
        "latitude": ad.get("latitude"),
        "longitude": ad.get("longitude"),
        "images": ad.get("images") or [],
        "contact_name": ad.get("full_name") or ad.get("account_name"),
        "contact_phone": phone,
        "contact_phone_status": phone_status,
        "contact_phone_source": "public_api" if phone else None,
        "published_at": published_at,
        "refreshed_at": refreshed_at,
        "fetched_at": fetched_at,
        "payload_hash": payload_hash,
        "raw_payload": ad,
    }

