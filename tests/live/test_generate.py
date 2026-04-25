from __future__ import annotations

import pytest

from image_bridge import ImageClient, ImageResult

from tests.live.assets import write_live_image
from tests.live.cases import GENERATE_CASES, LiveCase


@pytest.mark.live
@pytest.mark.live_generate
@pytest.mark.parametrize("live_case", GENERATE_CASES, ids=[case.id for case in GENERATE_CASES])
async def test_live_generate_matrix(live_case: LiveCase, request: pytest.FixtureRequest) -> None:
    live_case.ensure_required_env(request.config.getoption("--live-case"))
    client = ImageClient(live_case.build_config())
    try:
        result = await client.generate_image(live_case.build_generate_request())
    finally:
        await client.close()

    write_live_image(live_case.id, "generated", result.image_bytes, result.mime_type)

    assert isinstance(result, ImageResult)
    assert result.image_bytes
    assert result.mime_type.startswith("image/")
    assert isinstance(result.response_json, dict)
    assert result.model_version
