from __future__ import annotations

from pixelbridge.client import (
    GeminiAdapter,
    OpenAIChatAdapter,
    OpenAIImagesAdapter,
    _build_adapter,
)
from pixelbridge.types import ImageProvider, ProviderConfig


def test_openai_like_providers_use_openai_images_adapter_by_default() -> None:
    openai_adapter = _build_adapter(
        ProviderConfig(
            provider=ImageProvider.OPENAI,
            api_key="key",
            model="gpt-image-2",
            base_url="https://api.openai.com/v1",
        )
    )
    grok_adapter = _build_adapter(
        ProviderConfig(
            provider=ImageProvider.GROK,
            api_key="key",
            model="grok-imagine-1.0",
            base_url="https://api.x.ai/v1",
        )
    )

    assert isinstance(openai_adapter, OpenAIImagesAdapter)
    assert isinstance(grok_adapter, OpenAIImagesAdapter)


def test_gemini_provider_uses_gemini_adapter() -> None:
    adapter = _build_adapter(
        ProviderConfig(
            provider=ImageProvider.GEMINI,
            api_key="key",
            model="gemini-3.1-flash-image-preview",
            base_url="https://generativelanguage.googleapis.com/v1beta",
        )
    )

    assert isinstance(adapter, GeminiAdapter)


def test_protocol_override_uses_openai_chat_adapter() -> None:
    adapter = _build_adapter(
        ProviderConfig(
            provider=ImageProvider.OPENAI,
            api_key="key",
            model="gpt-image-2",
            base_url="https://api.openai.com/v1",
            extra_params={"_protocol": "openai_chat"},
        )
    )

    assert isinstance(adapter, OpenAIChatAdapter)
