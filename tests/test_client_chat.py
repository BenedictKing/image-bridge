from __future__ import annotations

import pytest

from image_bridge.client import (
    ImageClient,
    ImageClientError,
    _build_openai_chat_edit_payload,
    _build_openai_chat_generate_payload,
    _redact_payload_for_logging,
)
from image_bridge.types import EditRequest, GenerateRequest, ImageEditInput, ImageProvider, ProviderConfig


def test_build_openai_chat_generate_payload_uses_user_text_message() -> None:
    payload = _build_openai_chat_generate_payload(
        ProviderConfig(
            provider=ImageProvider.OPENAI,
            api_key="key",
            model="gpt-image-2",
            base_url="https://api.openai.com/v1",
            extra_params={"_protocol": "openai_chat", "temperature": 0.4},
        ),
        GenerateRequest(prompt="hello world", extra_params={"stream": False}),
    )

    assert payload["model"] == "gpt-image-2"
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"][0]["text"] == "hello world"
    assert payload["temperature"] == 0.4
    assert payload["stream"] is False
    assert "_protocol" not in payload


def test_build_openai_chat_edit_payload_converts_images_to_data_urls() -> None:
    payload = _build_openai_chat_edit_payload(
        ProviderConfig(
            provider=ImageProvider.OPENAI,
            api_key="key",
            model="gpt-image-2",
            base_url="https://api.openai.com/v1",
            extra_params={"_protocol": "openai_chat"},
        ),
        EditRequest(
            prompt="make it brighter",
            images=[ImageEditInput(data=b"png-bytes", mime_type="image/png")],
        ),
    )

    content = payload["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_build_openai_chat_edit_payload_rejects_mask() -> None:
    with pytest.raises(ImageClientError, match="mask is not supported"):
        _build_openai_chat_edit_payload(
            ProviderConfig(
                provider=ImageProvider.OPENAI,
                api_key="key",
                model="gpt-image-2",
                base_url="https://api.openai.com/v1",
                extra_params={"_protocol": "openai_chat"},
            ),
            EditRequest(
                prompt="edit it",
                images=[ImageEditInput(data=b"img", mime_type="image/png")],
                mask=ImageEditInput(data=b"mask", mime_type="image/png", name="mask.png"),
            ),
        )


def test_redact_payload_for_logging_summarizes_embedded_images() -> None:
    payload = _build_openai_chat_edit_payload(
        ProviderConfig(
            provider=ImageProvider.OPENAI,
            api_key="key",
            model="gpt-image-2",
            base_url="https://api.openai.com/v1",
            extra_params={"_protocol": "openai_chat"},
        ),
        EditRequest(
            prompt="make it brighter",
            images=[ImageEditInput(data=b"png-bytes", mime_type="image/png")],
        ),
    )

    redacted = _redact_payload_for_logging(payload)
    image_url = redacted["messages"][0]["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/png;sha256=")
    assert "bytes=" in image_url
    assert "base64" not in image_url


def test_image_client_uses_chat_adapter_when_protocol_overridden() -> None:
    client = ImageClient(
        ProviderConfig(
            provider=ImageProvider.OPENAI,
            api_key="key",
            model="gpt-image-2",
            base_url="https://api.openai.com/v1",
            extra_params={"_protocol": "openai_chat"},
        )
    )

    assert client._adapter.__class__.__name__ == "OpenAIChatAdapter"
