from __future__ import annotations

import base64

_MINIMAL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgN2Xh4QAAAAASUVORK5CYII="
)


def minimal_png_bytes() -> bytes:
    return base64.b64decode(_MINIMAL_PNG_BASE64)
