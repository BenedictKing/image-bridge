from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import pytest

from image_bridge import EditRequest, GenerateRequest, ImageEditInput, ImageProvider, ProviderConfig

from tests.live.assets import minimal_png_bytes

Capability = Literal["generate", "edit"]


@dataclass(frozen=True, slots=True)
class LiveCase:
    id: str
    provider: str
    protocol: str
    capability: Capability
    required_env: tuple[str, ...]
    config_env_prefix: str
    use_mask: bool = False
    generate_before_edit: bool = False
    generate_prompt: str = "A minimal test image with a single geometric shape on a plain background."
    edit_prompt: str = "Create a visibly different variant while keeping the subject simple."

    def build_config(self) -> ProviderConfig:
        timeout_value = os.getenv("IMAGE_BRIDGE_LIVE_TIMEOUT_SECONDS")
        timeout_seconds = float(timeout_value) if timeout_value else 300.0
        extra_params: dict[str, str] = {}
        if self.protocol != _default_protocol(self.provider):
            extra_params["_protocol"] = self.protocol
        return ProviderConfig(
            provider=ImageProvider(self.provider),
            api_key=_require_env(f"{self.config_env_prefix}_API_KEY"),
            model=_require_env(f"{self.config_env_prefix}_MODEL"),
            base_url=_provider_base_url(self.config_env_prefix, self.provider),
            timeout_seconds=timeout_seconds,
            extra_params=extra_params,
        )

    def build_generate_request(self) -> GenerateRequest:
        return GenerateRequest(
            prompt=self.generate_prompt,
            size="1024x1024",
        )

    def build_edit_request(self) -> EditRequest:
        image = ImageEditInput(data=minimal_png_bytes(), mime_type="image/png")
        mask = ImageEditInput(data=minimal_png_bytes(), mime_type="image/png", name="mask.png")
        return EditRequest(
            prompt=self.edit_prompt,
            images=[image],
            mask=mask if self.use_mask else None,
        )

    def ensure_required_env(self, selected_case_id: str | None = None) -> None:
        missing = [name for name in self.required_env if not _normalize_env(os.getenv(name))]
        explicit_case = selected_case_id or _normalize_env(os.getenv("IMAGE_BRIDGE_LIVE_CASE"))
        if missing and explicit_case == self.id:
            pytest.fail(f"Live case {self.id} is missing required env vars: {', '.join(missing)}")
        if missing:
            pytest.skip(f"Skipping live case {self.id}; missing env vars: {', '.join(missing)}")


OPENAI_GENERATE_CASES = [
    LiveCase(
        id="openai-images-generate",
        provider="openai",
        protocol="openai_images",
        capability="generate",
        required_env=("IMAGE_BRIDGE_OPENAI_API_KEY", "IMAGE_BRIDGE_OPENAI_MODEL"),
        config_env_prefix="IMAGE_BRIDGE_OPENAI",
    ),
    LiveCase(
        id="openai-chat-generate",
        provider="openai",
        protocol="openai_chat",
        capability="generate",
        required_env=("IMAGE_BRIDGE_OPENAI_API_KEY", "IMAGE_BRIDGE_OPENAI_MODEL"),
        config_env_prefix="IMAGE_BRIDGE_OPENAI",
    ),
]

GEMINI_GENERATE_CASES = [
    LiveCase(
        id="gemini-generate",
        provider="gemini",
        protocol="gemini_generate_content",
        capability="generate",
        required_env=("IMAGE_BRIDGE_GEMINI_API_KEY", "IMAGE_BRIDGE_GEMINI_MODEL"),
        config_env_prefix="IMAGE_BRIDGE_GEMINI",
    ),
]

GENERATE_CASES = [*OPENAI_GENERATE_CASES, *GEMINI_GENERATE_CASES]

EDIT_CASES = [
    LiveCase(
        id="openai-images-edit-mask",
        provider="openai",
        protocol="openai_images",
        capability="edit",
        required_env=("IMAGE_BRIDGE_OPENAI_API_KEY", "IMAGE_BRIDGE_OPENAI_MODEL"),
        config_env_prefix="IMAGE_BRIDGE_OPENAI",
        use_mask=True,
    ),
    LiveCase(
        id="openai-chat-edit",
        provider="openai",
        protocol="openai_chat",
        capability="edit",
        required_env=("IMAGE_BRIDGE_OPENAI_API_KEY", "IMAGE_BRIDGE_OPENAI_MODEL"),
        config_env_prefix="IMAGE_BRIDGE_OPENAI",
        generate_before_edit=True,
    ),
    LiveCase(
        id="openai-chat-edit-person-cat-to-dog",
        provider="openai",
        protocol="openai_chat",
        capability="edit",
        required_env=("IMAGE_BRIDGE_OPENAI_API_KEY", "IMAGE_BRIDGE_OPENAI_MODEL"),
        config_env_prefix="IMAGE_BRIDGE_OPENAI",
        generate_before_edit=True,
        generate_prompt="写实摄影风格，单人半身正面肖像，一名成年人双手抱着一只猫，猫完整可见，人物与猫位于画面中央，背景为纯浅灰色，无其他物体或装饰，光线均匀，构图简单清晰。",
        edit_prompt="基于输入图片做最小必要修改，不要重绘整张图。保留同一个人物、相同的脸、发型、衣服、手部位置、抱姿、镜头角度、构图、背景、光线和色调。仅将人物怀里的猫替换为一只体型相近的小狗，位置、朝向、大小与原猫尽量一致，使其看起来像在原图上局部编辑后的结果。除把猫改成狗之外，不要改变任何其他内容。",
    ),
    LiveCase(
        id="gemini-edit-reference",
        provider="gemini",
        protocol="gemini_generate_content",
        capability="edit",
        required_env=("IMAGE_BRIDGE_GEMINI_API_KEY", "IMAGE_BRIDGE_GEMINI_MODEL"),
        config_env_prefix="IMAGE_BRIDGE_GEMINI",
    ),
]


def _default_protocol(provider: str) -> str:
    if provider == "gemini":
        return "gemini_generate_content"
    return "openai_images"


def _normalize_env(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _require_env(name: str) -> str:
    value = _normalize_env(os.getenv(name))
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _provider_base_url(prefix: str, provider: str) -> str:
    configured = _normalize_env(os.getenv(f"{prefix}_BASE_URL"))
    if configured is not None:
        return configured
    if provider == "gemini":
        return "https://generativelanguage.googleapis.com/v1beta"
    return "https://api.openai.com/v1"
