# image-models

`image-models` 是一个共享的图片生成/编辑访问层，面向多个供应商和协议形状，公共接口保持最小稳定。

## 稳定公共接口

- `ProviderConfig`
- `GenerateRequest`
- `EditRequest`
- `ImageEditInput`
- `ImageResult`
- `ImageClient.generate_image()`
- `ImageClient.edit_image()`

## 内部协议支持

- `openai_images`
- `openai_chat`
- `gemini_generate_content`

## 设计目标

- 业务层不感知协议差异
- 供应商差异通过 `extra_params` 下沉
- 在不扩大公共 API 的前提下保留兼容面
