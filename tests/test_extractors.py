from __future__ import annotations

import base64

import pytest

from image_bridge.client import (
    ImageClientError,
    _extract_gemini_image,
    _extract_openai_chat_data_url,
    _extract_openai_chat_image_part,
    _extract_openai_image,
)


def test_extract_openai_image_reads_b64_json() -> None:
    image_bytes = b"fake-png-bytes"
    payload = {
        "data": [
            {
                "b64_json": base64.b64encode(image_bytes).decode("utf-8"),
                "mime_type": "image/png",
            }
        ]
    }

    decoded, mime_type = _extract_openai_image(payload)

    assert decoded == image_bytes
    assert mime_type == "image/png"


def test_extract_gemini_image_reads_inline_data() -> None:
    image_bytes = b"fake-webp-bytes"
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/webp",
                                "data": base64.b64encode(image_bytes).decode("utf-8"),
                            }
                        }
                    ]
                }
            }
        ]
    }

    decoded, mime_type = _extract_gemini_image(payload)

    assert decoded == image_bytes
    assert mime_type == "image/webp"


def test_extract_openai_chat_image_reads_nested_output_image() -> None:
    image_bytes = b"fake-jpeg-bytes"
    message = {
        "content": [
            {
                "type": "output_image",
                "image": {
                    "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
                    "mime_type": "image/jpeg",
                },
            }
        ]
    }

    decoded, mime_type = _extract_openai_chat_image_part(message) or (None, None)

    assert decoded == image_bytes
    assert mime_type == "image/jpeg"


def test_extract_openai_chat_data_url_reads_embedded_data() -> None:
    image_bytes = b"fake-inline-png"
    data_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"

    decoded, mime_type = _extract_openai_chat_data_url(data_url) or (None, None)

    assert decoded == image_bytes
    assert mime_type == "image/png"


def test_extract_openai_image_raises_when_missing_image() -> None:
    with pytest.raises(ImageClientError, match="no image bytes"):
        _extract_openai_image({"data": [{}]})
