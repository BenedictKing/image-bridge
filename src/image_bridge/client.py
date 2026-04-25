from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from image_bridge.types import (
    EditRequest,
    GenerateRequest,
    ImageProvider,
    ImageResult,
    ProviderConfig,
)

logger = logging.getLogger(__name__)


class ImageClientError(RuntimeError):
    """Raised when the shared image client cannot complete a request."""


class ProviderAdapter(ABC):
    """Internal protocol adapter used by ``ImageClient`` implementations."""

    _MARKDOWN_IMAGE_URL_RE = re.compile(r"!\[[^\]]*\]\(((?:https?://|data:)[^)]+)\)")

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    async def generate_image(self, http: httpx.AsyncClient, request: GenerateRequest) -> ImageResult:
        """Generate an image using the provider-specific protocol."""

    @abstractmethod
    async def edit_image(self, http: httpx.AsyncClient, request: EditRequest) -> ImageResult:
        """Edit or reference-generate an image using the provider-specific protocol."""

    @staticmethod
    def _decode_base64_image(data: str, mime_type: str = "image/png") -> tuple[bytes, str]:
        return base64.b64decode(data), mime_type

    @classmethod
    def _extract_markdown_image_url(cls, text: str) -> str | None:
        match = cls._MARKDOWN_IMAGE_URL_RE.search(text)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _to_data_url(data: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"


class ImageClient:
    """Stable public client exposing only ``generate_image`` and ``edit_image``."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._http: httpx.AsyncClient | None = None
        self._adapter = _build_adapter(config)

    def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=self._config.timeout_seconds)
        return self._http

    async def generate_image(self, request: GenerateRequest) -> ImageResult:
        """Generate an image using the configured provider."""
        return await self._adapter.generate_image(self._get_http(), request)

    async def edit_image(self, request: EditRequest) -> ImageResult:
        """Edit or reference-generate an image using the configured provider."""
        return await self._adapter.edit_image(self._get_http(), request)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()


class OpenAIImagesAdapter(ProviderAdapter):
    """Internal adapter for OpenAI-compatible ``/images/*`` protocols."""

    async def generate_image(self, http: httpx.AsyncClient, request: GenerateRequest) -> ImageResult:
        payload = _build_openai_images_generate_payload(self.config, request)
        _log_upstream_request("openai_images.generate", payload)
        response = await http.post(
            f"{self.config.base_url.rstrip('/')}/images/generations",
            headers=_build_json_headers(self.config),
            json=payload,
        )
        response.raise_for_status()
        payload_json = response.json()
        image_bytes, mime_type = _extract_openai_image(payload_json)
        return ImageResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            model_version=str(payload_json.get("model") or self.config.model),
            response_json=payload_json,
        )

    async def edit_image(self, http: httpx.AsyncClient, request: EditRequest) -> ImageResult:
        payload = _build_openai_images_edit_payload(self.config, request)
        _log_upstream_request("openai_images.edit", payload)
        response = await http.post(
            f"{self.config.base_url.rstrip('/')}/images/edits",
            headers=_build_json_headers(self.config),
            json=payload,
        )
        response.raise_for_status()
        payload_json = response.json()
        image_bytes, mime_type = _extract_openai_image(payload_json)
        return ImageResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            model_version=str(payload_json.get("model") or self.config.model),
            response_json=payload_json,
        )


class OpenAIChatAdapter(ProviderAdapter):
    """Internal adapter for OpenAI-compatible ``/chat/completions`` image flows."""

    async def generate_image(self, http: httpx.AsyncClient, request: GenerateRequest) -> ImageResult:
        payload = _build_openai_chat_generate_payload(self.config, request)
        _log_upstream_request("openai_chat.generate", payload)
        response = await http.post(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            headers=_build_json_headers(self.config),
            json=payload,
        )
        response.raise_for_status()
        payload_json = response.json()
        image_bytes, mime_type = await _extract_openai_chat_image(http, payload_json)
        return ImageResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            model_version=str(payload_json.get("model") or self.config.model),
            response_json=payload_json,
        )

    async def edit_image(self, http: httpx.AsyncClient, request: EditRequest) -> ImageResult:
        payload = _build_openai_chat_edit_payload(self.config, request)
        _log_upstream_request("openai_chat.edit", payload)
        response = await http.post(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            headers=_build_json_headers(self.config),
            json=payload,
        )
        response.raise_for_status()
        payload_json = response.json()
        image_bytes, mime_type = await _extract_openai_chat_image(http, payload_json)
        return ImageResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            model_version=str(payload_json.get("model") or self.config.model),
            response_json=payload_json,
        )


class GeminiAdapter(ProviderAdapter):
    """Internal adapter for Gemini ``generateContent`` image flows."""

    async def generate_image(self, http: httpx.AsyncClient, request: GenerateRequest) -> ImageResult:
        generation_config: dict[str, Any] = {"responseModalities": ["TEXT", "IMAGE"]}
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": generation_config,
        }
        payload.update(_public_extra_params(self.config.extra_params))
        payload.update(_public_extra_params(request.extra_params))
        _log_upstream_request("gemini.generate", payload)

        response = await http.post(
            f"{self.config.base_url.rstrip('/')}/models/{self.config.model}:generateContent?key={self.config.api_key}",
            json=payload,
        )
        response.raise_for_status()
        payload_json = response.json()
        image_bytes, mime_type = _extract_gemini_image(payload_json)
        return ImageResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            model_version=str(payload_json.get("modelVersion") or self.config.model),
            response_json=payload_json,
        )

    async def edit_image(self, http: httpx.AsyncClient, request: EditRequest) -> ImageResult:
        if not request.images:
            raise ImageClientError("edit_image requires at least one input image")

        parts: list[dict[str, Any]] = []
        for image in request.images:
            parts.append(
                {
                    "inlineData": {
                        "mimeType": image.mime_type,
                        "data": base64.b64encode(image.data).decode("utf-8"),
                    }
                }
            )
        parts.append({"text": request.prompt})
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }
        payload.update(_public_extra_params(self.config.extra_params))
        payload.update(_public_extra_params(request.extra_params))
        _log_upstream_request("gemini.edit", payload)

        response = await http.post(
            f"{self.config.base_url.rstrip('/')}/models/{self.config.model}:generateContent?key={self.config.api_key}",
            json=payload,
        )
        response.raise_for_status()
        payload_json = response.json()
        image_bytes, mime_type = _extract_gemini_image(payload_json)
        return ImageResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            model_version=str(payload_json.get("modelVersion") or self.config.model),
            response_json=payload_json,
        )


def _build_adapter(config: ProviderConfig) -> ProviderAdapter:
    protocol = _resolve_protocol(config)
    if protocol == "gemini_generate_content":
        return GeminiAdapter(config)
    if protocol == "openai_chat":
        return OpenAIChatAdapter(config)
    if protocol == "openai_images":
        return OpenAIImagesAdapter(config)
    raise ImageClientError(f"Unsupported image protocol: {protocol}")


def _resolve_protocol(config: ProviderConfig) -> str:
    protocol = config.extra_params.get("_protocol")
    if isinstance(protocol, str) and protocol:
        return protocol
    if config.provider == ImageProvider.GEMINI:
        return "gemini_generate_content"
    if config.provider in {ImageProvider.OPENAI, ImageProvider.GROK, ImageProvider.JIMENG}:
        return "openai_images"
    raise ImageClientError(f"Unsupported image provider: {config.provider}")


def _build_json_headers(config: ProviderConfig) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}",
    }
    headers.update(config.extra_headers)
    return headers


def _public_extra_params(extra_params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in extra_params.items() if not k.startswith("_")}


def _is_request_logging_enabled() -> bool:
    value = os.getenv("IMAGE_BRIDGE_LOG_UPSTREAM_REQUESTS", "")
    return value.lower() in {"1", "true", "yes", "on"}


def _redact_payload_for_logging(value: Any) -> Any:
    if isinstance(value, dict):
        if "image_url" in value and isinstance(value["image_url"], dict):
            image_url = value["image_url"].get("url")
            if isinstance(image_url, str):
                return {
                    **value,
                    "image_url": {
                        **value["image_url"],
                        "url": _summarize_data_url(image_url),
                    },
                }
        if "data" in value and isinstance(value["data"], str):
            return {
                **value,
                "data": _summarize_base64_data(value["data"]),
            }
        return {key: _redact_payload_for_logging(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_payload_for_logging(item) for item in value]
    return value


def _summarize_data_url(value: str) -> str:
    decoded = _extract_openai_chat_data_url(value)
    if decoded is None:
        return value
    image_bytes, mime_type = decoded
    digest = hashlib.sha256(image_bytes).hexdigest()[:12]
    return f"data:{mime_type};sha256={digest};bytes={len(image_bytes)}"


def _summarize_base64_data(value: str) -> str:
    try:
        image_bytes = base64.b64decode(value)
    except Exception:
        return f"base64:chars={len(value)}"
    digest = hashlib.sha256(image_bytes).hexdigest()[:12]
    return f"base64:sha256={digest};bytes={len(image_bytes)}"


def _log_upstream_request(endpoint: str, payload: dict[str, Any]) -> None:
    if not _is_request_logging_enabled():
        return
    logger.warning(
        "ImageBridge upstream request %s\n%s",
        endpoint,
        json.dumps(_redact_payload_for_logging(payload), ensure_ascii=False, indent=2, sort_keys=True),
    )


def _build_openai_images_generate_payload(config: ProviderConfig, request: GenerateRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": config.model,
        "prompt": request.prompt,
    }
    if request.size:
        payload["size"] = request.size
    if request.quality:
        payload["quality"] = request.quality
    if request.output_format:
        payload["output_format"] = request.output_format
    if request.background:
        payload["background"] = request.background
    if request.moderation:
        payload["moderation"] = request.moderation
    if request.n is not None:
        payload["n"] = request.n
    payload.update(_public_extra_params(config.extra_params))
    payload.update(_public_extra_params(request.extra_params))
    return payload


def _build_openai_images_edit_payload(config: ProviderConfig, request: EditRequest) -> dict[str, Any]:
    if not request.images:
        raise ImageClientError("edit_image requires at least one input image")
    payload: dict[str, Any] = {
        "model": config.model,
        "prompt": request.prompt,
        "image": [
            {
                "name": image.name,
                "mime_type": image.mime_type,
                "data": base64.b64encode(image.data).decode("utf-8"),
            }
            for image in request.images
        ],
    }
    if request.mask is not None:
        payload["mask"] = {
            "name": request.mask.name,
            "mime_type": request.mask.mime_type,
            "data": base64.b64encode(request.mask.data).decode("utf-8"),
        }
    if request.size:
        payload["size"] = request.size
    if request.quality:
        payload["quality"] = request.quality
    if request.output_format:
        payload["output_format"] = request.output_format
    if request.background:
        payload["background"] = request.background
    if request.moderation:
        payload["moderation"] = request.moderation
    payload.update(_public_extra_params(config.extra_params))
    payload.update(_public_extra_params(request.extra_params))
    return payload


def _build_openai_chat_generate_payload(config: ProviderConfig, request: GenerateRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": request.prompt}],
            }
        ],
    }
    payload.update(_public_extra_params(config.extra_params))
    payload.update(_public_extra_params(request.extra_params))
    return payload


def _build_openai_chat_edit_payload(config: ProviderConfig, request: EditRequest) -> dict[str, Any]:
    if not request.images:
        raise ImageClientError("edit_image requires at least one input image")
    if request.mask is not None:
        raise ImageClientError("mask is not supported when using openai_chat protocol")
    content: list[dict[str, Any]] = [{"type": "text", "text": request.prompt}]
    for image in request.images:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": ProviderAdapter._to_data_url(image.data, image.mime_type),
                },
            }
        )
    payload: dict[str, Any] = {
        "model": config.model,
        "messages": [{"role": "user", "content": content}],
    }
    payload.update(_public_extra_params(config.extra_params))
    payload.update(_public_extra_params(request.extra_params))
    return payload


def _extract_openai_image(payload: dict[str, Any]) -> tuple[bytes, str]:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ImageClientError("Image API response returned no data")
    first = data[0]
    if not isinstance(first, dict):
        raise ImageClientError("Image API response item is invalid")
    image_base64 = first.get("b64_json") or first.get("image_base64")
    if isinstance(image_base64, str) and image_base64:
        mime_type = str(first.get("mime_type") or "image/png")
        return base64.b64decode(image_base64), mime_type
    raise ImageClientError("Image API response returned no image bytes")


def _extract_openai_chat_text(payload: dict[str, Any]) -> str:
    message = _extract_openai_chat_message(payload)
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    texts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") in {"text", "output_text"}:
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
    return "\n".join(texts).strip()


def _extract_openai_chat_message(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ImageClientError("Chat completions response returned no choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ImageClientError("Chat completions response returned an invalid choice payload")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ImageClientError("Chat completions response returned no message")
    return message


def _extract_openai_chat_data_url(value: str) -> tuple[bytes, str] | None:
    if not value.startswith("data:") or ";base64," not in value:
        return None
    header, data = value.split(",", 1)
    mime_type = header.removeprefix("data:").split(";", 1)[0] or "image/png"
    return base64.b64decode(data), mime_type


def _extract_openai_chat_image_part(message: dict[str, Any]) -> tuple[bytes, str] | None:
    content = message.get("content")
    if not isinstance(content, list):
        return None
    for part in content:
        if not isinstance(part, dict):
            continue
        image_base64 = part.get("image_base64") or part.get("b64_json")
        mime_type = part.get("mime_type") or part.get("mimeType") or "image/png"
        if isinstance(image_base64, str) and image_base64:
            return base64.b64decode(image_base64), str(mime_type)
        if part.get("type") in {"image", "output_image"}:
            image_data = part.get("image")
            if isinstance(image_data, dict):
                embedded_b64 = image_data.get("image_base64") or image_data.get("b64_json")
                embedded_mime = image_data.get("mime_type") or image_data.get("mimeType") or mime_type
                if isinstance(embedded_b64, str) and embedded_b64:
                    return base64.b64decode(embedded_b64), str(embedded_mime)
        image_url = part.get("image_url")
        if isinstance(image_url, dict):
            image_url = image_url.get("url")
        if isinstance(image_url, str) and image_url:
            decoded = _extract_openai_chat_data_url(image_url)
            if decoded is not None:
                return decoded
    return None


def _extract_openai_chat_image_url(message: dict[str, Any]) -> str | None:
    content = message.get("content")
    if isinstance(content, str):
        return ProviderAdapter._extract_markdown_image_url(content)
    if not isinstance(content, list):
        return None
    for part in content:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str):
            image_url = ProviderAdapter._extract_markdown_image_url(text)
            if image_url:
                return image_url
    return None


async def _download_image_from_url(http: httpx.AsyncClient, image_url: str) -> tuple[bytes, str]:
    response = await http.get(image_url)
    response.raise_for_status()
    mime_type = response.headers.get("content-type", "image/png").split(";", 1)[0].strip() or "image/png"
    return response.content, mime_type


async def _extract_openai_chat_image(
    http: httpx.AsyncClient,
    payload: dict[str, Any],
) -> tuple[bytes, str]:
    message = _extract_openai_chat_message(payload)
    image_part = _extract_openai_chat_image_part(message)
    if image_part is not None:
        return image_part
    image_url = _extract_openai_chat_image_url(message)
    if image_url:
        decoded = _extract_openai_chat_data_url(image_url)
        if decoded is not None:
            return decoded
        return await _download_image_from_url(http, image_url)
    raise ImageClientError(
        f"Chat completions endpoint returned no image. Model said: {_extract_openai_chat_text(payload) or 'No text returned.'}"
    )


def _extract_gemini_image(payload: dict[str, Any]) -> tuple[bytes, str]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ImageClientError("Gemini response returned no candidates")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if not isinstance(part, dict):
                continue
            inline = part.get("inlineData") or part.get("inline_data")
            if not isinstance(inline, dict):
                continue
            data = inline.get("data")
            if isinstance(data, str) and data:
                mime_type = str(inline.get("mimeType") or inline.get("mime_type") or "image/png")
                return base64.b64decode(data), mime_type
    raise ImageClientError("Gemini response returned no image bytes")
