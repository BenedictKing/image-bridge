from __future__ import annotations

import pytest

from image_bridge import ImageClient, ImageEditInput, ImageResult

from tests.live.assets import write_live_image
from tests.live.cases import EDIT_CASES, LiveCase


@pytest.mark.live
@pytest.mark.live_edit
@pytest.mark.parametrize("live_case", EDIT_CASES, ids=[case.id for case in EDIT_CASES])
async def test_live_edit_matrix(live_case: LiveCase, request: pytest.FixtureRequest) -> None:
    live_case.ensure_required_env(request.config.getoption("--live-case"))
    client = ImageClient(live_case.build_config())
    try:
        edit_request = live_case.build_edit_request()
        pre_edit_generate_requests = live_case.build_pre_edit_generate_requests()
        if pre_edit_generate_requests:
            generated_images: list[ImageEditInput] = []
            multiple_generated_inputs = len(pre_edit_generate_requests) > 1
            for index, generate_request in enumerate(pre_edit_generate_requests, start=1):
                generated = await client.generate_image(generate_request)
                generated_path = write_live_image(
                    live_case.id,
                    f"generated-{index}" if multiple_generated_inputs else "generated",
                    generated.image_bytes,
                    generated.mime_type,
                )
                generated_images.append(
                    ImageEditInput(
                        data=generated.image_bytes,
                        mime_type=generated.mime_type,
                        name=generated_path.name,
                    )
                )
            edit_request.images = generated_images
        if live_case.pre_edit_generate_prompts:
            assert len(edit_request.images) >= 2
        result = await client.edit_image(edit_request)
    finally:
        await client.close()

    write_live_image(live_case.id, "edited", result.image_bytes, result.mime_type)

    assert isinstance(result, ImageResult)
    assert result.image_bytes
    assert result.mime_type.startswith("image/")
    assert isinstance(result.response_json, dict)
    assert result.model_version
