# ImageBridge

[English](README.md) | [简体中文](README.zh-CN.md)

ImageBridge 是一个轻量的 Python 图片生成/编辑桥接层，用来统一不同供应商与不同 wire protocol 的访问方式。

它为业务代码提供**稳定的公共 API**，同时把供应商与协议差异留在内部处理。当前实现支持 OpenAI-compatible 图片接口、OpenAI-compatible chat 图片流，以及 Gemini `generateContent` 图片流。

## 设计目标

1. **公共 API 保持最小化**：只暴露 `generate_image` 和 `edit_image`
2. **隐藏协议差异**：通过内部适配器和路由处理 `/images/*`、`/chat/completions`、`generateContent` 的差异
3. **控制供应商扩展面**：通过显式扩展点承载差异，而不是把 wire 细节泄漏到业务层
4. **务实优先**：优先提供稳定窄接口，而不是过早抽象所有图片能力

## 稳定公共 API

- `ProviderConfig`
- `GenerateRequest`
- `EditRequest`
- `ImageEditInput`
- `ImageResult`
- `ImageClient.generate_image()`
- `ImageClient.edit_image()`

## 快速开始

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

## 支持的供应商与默认协议

| Provider | Generation | Edit | 默认协议 |
|----------|-----------|------|----------|
| openai | ✅ | ✅ | OpenAI Image API |
| grok | ✅ | ✅ | OpenAI-compatible Image API |
| jimeng | ✅ | ✅ | OpenAI-compatible Image API |
| gemini | ✅ | ✅ | Gemini `generateContent` |

## 内部协议切换

公共 API 不暴露 protocol，但共享层内部支持保留参数切换：

- `ProviderConfig.extra_params["_protocol"] = "openai_images"`
- `ProviderConfig.extra_params["_protocol"] = "openai_chat"`
- `ProviderConfig.extra_params["_protocol"] = "gemini_generate_content"`

示例：

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

说明：

- `_protocol` 是共享层内部实现细节，不建议在业务层大面积扩散
- 未显式指定时，`gemini` 默认走 `generateContent`，其余供应商默认走 `openai_images`
- `_protocol` 会在请求发出前被剔除，不会透传到上游供应商

## mask 支持边界

- `openai_images` 和兼容 `/images/edits` 的路径支持 `EditRequest.mask`
- `gemini_generate_content` 当前支持参考图，但没有显式映射公共 `mask` 字段
- `openai_chat` 当前**不支持 mask**，会直接抛出清晰错误，而不是做伪兼容

这样可以确保 `EditRequest.mask` 的语义足够明确，不会因为协议不同而产生误解。

## 自动化 API 文档

项目已提供 MkDocs + mkdocstrings 配置：

- 配置文件：`mkdocs.yml`
- 文档目录：`docs/`

本地预览：

```bash
python -m pip install -e .[dev]
mkdocs serve
```

静态构建：

```bash
python -m pip install -e .[dev]
mkdocs build
```

## 当前暂不支持

- Responses API image tool
- `previous_response_id`
- 多轮图片会话
- partial image streaming
- file ID / 上传抽象
- 视频生成抽象

## 扩展点

ImageBridge 有意不把协议差异公开到公共 API，但仍保留两个扩展点来承载供应商差异：

- `ProviderConfig.extra_params`：供应商级默认参数
- `GenerateRequest.extra_params` / `EditRequest.extra_params`：单次请求参数

典型适用场景：

- OpenAI-compatible 供应商在 `/images/*` 或 `/chat/completions` 上增加私有字段
- 某些供应商对 `size`、`quality` 或输出字段有额外约束

核心目标是：**公共 API 保持稳定，不可避免的差异通过显式扩展点下沉**。
