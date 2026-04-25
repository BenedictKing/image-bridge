from __future__ import annotations

import base64
from datetime import datetime, UTC
from pathlib import Path

_MINIMAL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgN2Xh4QAAAAASUVORK5CYII="
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TMP_DIR = _PROJECT_ROOT / "tmp"


def minimal_png_bytes() -> bytes:
    return base64.b64decode(_MINIMAL_PNG_BASE64)


def suffix_for_mime_type(mime_type: str) -> str:
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }.get(mime_type, ".bin")


def write_live_image(case_id: str, stage: str, image_bytes: bytes, mime_type: str) -> Path:
    _TMP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = _TMP_DIR / f"{case_id}-{stage}-{timestamp}{suffix_for_mime_type(mime_type)}"
    path.write_bytes(image_bytes)
    return path
