from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ImageProvider(StrEnum):
    """Supported provider families for the shared image client."""

    OPENAI = "openai"
    GROK = "grok"
    JIMENG = "jimeng"
    GEMINI = "gemini"


@dataclass(slots=True)
class ProviderConfig:
    """Provider-level configuration used by ``ImageClient``."""

    provider: ImageProvider
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float = 300.0
    extra_headers: dict[str, str] = field(default_factory=dict)
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ImageEditInput:
    """Binary image input used for edit/reference-image requests."""

    data: bytes
    mime_type: str
    name: str = "image.png"


@dataclass(slots=True)
class GenerateRequest:
    """Stable public request model for image generation."""

    prompt: str
    size: str | None = None
    quality: str | None = None
    output_format: str | None = None
    background: str | None = None
    moderation: str | None = None
    n: int | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EditRequest:
    """Stable public request model for image editing/reference generation."""

    prompt: str
    images: list[ImageEditInput]
    mask: ImageEditInput | None = None
    size: str | None = None
    quality: str | None = None
    output_format: str | None = None
    background: str | None = None
    moderation: str | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ImageResult:
    """Normalized image result returned by the shared client."""

    image_bytes: bytes
    mime_type: str
    model_version: str
    response_json: dict[str, Any]
