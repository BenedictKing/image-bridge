# ImageBridge

[English](README.md) | [简体中文](README.zh-CN.md)

ImageBridge is a lightweight Python bridge for image generation and editing across providers and wire protocols.

It provides a **stable public API** for application code while keeping provider-specific protocol details internal. The current implementation supports OpenAI-compatible image endpoints, OpenAI-compatible chat-based image flows, and Gemini `generateContent` image flows.

## Design goals

1. **Keep the public API minimal**: only expose `generate_image` and `edit_image`
2. **Hide protocol differences** behind provider adapters and internal routing
3. **Support provider variation** through explicit extension points instead of leaking wire details into app code
4. **Stay pragmatic**: prefer a narrow, stable surface over premature abstraction of every image capability

## Stable public API

- `ProviderConfig`
- `GenerateRequest`
- `EditRequest`
- `ImageEditInput`
- `ImageResult`
- `ImageClient.generate_image()`
- `ImageClient.edit_image()`

## Quick start

```python
from image_bridge import GenerateRequest, ImageClient, ImageProvider, ProviderConfig

client = ImageClient(
    ProviderConfig(
        provider=ImageProvider.OPENAI,
        api_key="sk-xxx",
        model="gpt-image-2",
        base_url="https://api.openai.com/v1",
    )
)

result = await client.generate_image(
    GenerateRequest(
        prompt="A professional portrait in a cozy cafe",
        size="1024x1536",
        quality="high",
    )
)

# result.image_bytes: bytes
# result.mime_type: str
# result.model_version: str
```

## Supported providers and default protocols

| Provider | Generation | Edit | Default protocol |
|----------|-----------|------|------------------|
| openai | ✅ | ✅ | OpenAI Image API |
| grok | ✅ | ✅ | OpenAI-compatible Image API |
| jimeng | ✅ | ✅ | OpenAI-compatible Image API |
| gemini | ✅ | ✅ | Gemini `generateContent` |

## Internal protocol override

The public API does not expose protocol selection, but the shared layer supports internal overrides via reserved parameters:

- `ProviderConfig.extra_params["_protocol"] = "openai_images"`
- `ProviderConfig.extra_params["_protocol"] = "openai_chat"`
- `ProviderConfig.extra_params["_protocol"] = "gemini_generate_content"`

Example:

```python
client = ImageClient(
    ProviderConfig(
        provider=ImageProvider.OPENAI,
        api_key="sk-xxx",
        model="gpt-image-2",
        base_url="https://api.openai.com/v1",
        extra_params={"_protocol": "openai_chat"},
    )
)
```

Notes:

- `_protocol` is an internal implementation detail and should not be widely exposed in application code
- Without an explicit override, `gemini` uses `generateContent` and the other providers default to `openai_images`
- `_protocol` is stripped before requests are sent to upstream providers

## Mask support boundaries

- `openai_images` and compatible `/images/edits` flows support `EditRequest.mask`
- `gemini_generate_content` currently supports reference images but does not explicitly map the public `mask` field
- `openai_chat` currently **does not support mask** and will raise a clear error instead of pretending to support it

This keeps the semantics of `EditRequest.mask` explicit and avoids protocol-specific ambiguity.

## Live tests

The repository includes opt-in live tests that call real upstream APIs and models through the public API.

Use them to verify that `image-bridge` still works as a dependency in downstream projects under real provider conditions.

Default behavior:

- Live tests do **not** run as part of normal `pytest`
- They may consume API quota and are subject to provider rate limits or transient upstream failures

Minimum environment variables:

You can start by copying `.env.example` to `.env` and filling in only the providers you want to exercise.

```bash
export IMAGE_BRIDGE_OPENAI_API_KEY=...
export IMAGE_BRIDGE_OPENAI_MODEL=gpt-image-1
export IMAGE_BRIDGE_GEMINI_API_KEY=...
export IMAGE_BRIDGE_GEMINI_MODEL=gemini-2.5-flash-image-preview
```

Optional environment variables:

```bash
export IMAGE_BRIDGE_OPENAI_BASE_URL=https://api.openai.com/v1
export IMAGE_BRIDGE_GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
export IMAGE_BRIDGE_LIVE_TIMEOUT_SECONDS=300
```

Run all live tests:

```bash
uv run --extra test python -m pytest --run-live tests/live -q
```

Run a single live case:

```bash
uv run --extra test python -m pytest --run-live --live-case openai-images-generate tests/live/test_generate.py -q
```

Replay the reusable person-holds-cat then cat-to-dog edit case:

```bash
uv run --env-file .env --extra test python -m pytest --run-live --live-case openai-chat-edit-person-cat-to-dog tests/live/test_edit.py -q
```

To print sanitized upstream request payloads during debugging:

```bash
IMAGE_BRIDGE_LOG_UPSTREAM_REQUESTS=1 uv run --env-file .env --extra test python -m pytest --run-live --live-case openai-chat-edit-person-cat-to-dog tests/live/test_edit.py -q -o log_cli=true --log-cli-level=WARNING
```

Current boundaries:

- `openai_chat` does not support `mask`
- `gemini_generate_content` currently does not expose a public `mask` mapping

## Automated API documentation

The project includes MkDocs + mkdocstrings configuration:

- config: `mkdocs.yml`
- docs directory: `docs/`

Preview locally:

```bash
python -m pip install -e .[dev]
mkdocs serve
```

Build static docs:

```bash
python -m pip install -e .[dev]
mkdocs build
```

## Out of scope for now

- Responses API image tool
- `previous_response_id`
- multi-turn image sessions
- partial image streaming
- file ID / uploads abstraction
- video generation abstraction

## Extension points

ImageBridge intentionally keeps protocol-specific differences out of the public API, but leaves two extension points for provider variation:

- `ProviderConfig.extra_params`: provider-level default parameters
- `GenerateRequest.extra_params` / `EditRequest.extra_params`: per-request parameters

Typical uses:

- OpenAI-compatible providers that add custom request fields on `/images/*` or `/chat/completions`
- Provider-specific constraints or extensions for `size`, `quality`, or output fields

The design goal is simple: **keep the public API stable and push unavoidable variation into explicit extension points**.
