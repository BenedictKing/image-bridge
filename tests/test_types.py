from __future__ import annotations

from image_models.types import EditRequest, GenerateRequest, ImageEditInput


def test_generate_request_defaults() -> None:
    request = GenerateRequest(prompt="hello")

    assert request.prompt == "hello"
    assert request.size is None
    assert request.extra_params == {}


def test_edit_request_accepts_images_and_mask() -> None:
    image = ImageEditInput(data=b"img", mime_type="image/png")
    mask = ImageEditInput(data=b"mask", mime_type="image/png", name="mask.png")
    request = EditRequest(prompt="edit it", images=[image], mask=mask)

    assert len(request.images) == 1
    assert request.mask is not None
    assert request.mask.name == "mask.png"
