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
        if live_case.generate_before_edit:
            generated = await client.generate_image(live_case.build_generate_request())
            generated_path = write_live_image(
                live_case.id,
                "generated",
                generated.image_bytes,
                generated.mime_type,
            )
            edit_request.images = [
                ImageEditInput(
                    data=generated.image_bytes,
                    mime_type=generated.mime_type,
                    name=generated_path.name,
                )
            ]
        result = await client.edit_image(edit_request)
    finally:
        await client.close()

    write_live_image(live_case.id, "edited", result.image_bytes, result.mime_type)

    assert isinstance(result, ImageResult)
    assert result.image_bytes
    assert result.mime_type.startswith("image/")
    assert isinstance(result.response_json, dict)
    assert result.model_version
