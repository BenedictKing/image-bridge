# ImageBridge

ImageBridge is a lightweight Python bridge for image generation and editing across providers and wire protocols.

It offers a stable public API for application code while keeping provider-specific protocol handling internal.

## Stable public API

- `ProviderConfig`
- `GenerateRequest`
- `EditRequest`
- `ImageEditInput`
- `ImageResult`
- `ImageClient.generate_image()`
- `ImageClient.edit_image()`

## Internal protocol support

- `openai_images`
- `openai_chat`
- `gemini_generate_content`

## Design goals

- Keep application code unaware of protocol differences
- Push provider variation into explicit extension points
- Preserve compatibility without expanding the public API unnecessarily

## Language

- English README: `README.md`
- Chinese README: `README.zh-CN.md`
