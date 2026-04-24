from __future__ import annotations

import pytest

from image_bridge import ImageClient, ImageResult

from tests.live.cases import EDIT_CASES, LiveCase


@pytest.mark.live
@pytest.mark.live_edit
@pytest.mark.parametrize("live_case", EDIT_CASES, ids=[case.id for case in EDIT_CASES])
async def test_live_edit_matrix(live_case: LiveCase, request: pytest.FixtureRequest) -> None:
    live_case.ensure_required_env(request.config.getoption("--live-case"))
    client = ImageClient(live_case.build_config())
    try:
        result = await client.edit_image(live_case.build_edit_request())
    finally:
        await client.close()

    assert isinstance(result, ImageResult)
    assert result.image_bytes
    assert result.mime_type.startswith("image/")
    assert isinstance(result.response_json, dict)
    assert result.model_version
