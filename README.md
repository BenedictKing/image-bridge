# Image Models
统一多供应商图片生成/编辑抽象包。

用于 best-shot 和 best-outfit 共享图片模型访问层。

## 设计原则

1. **接口最小化**：对外只暴露两个稳定入口：`generate_image`、`edit_image`
2. **供应商可替换**：OpenAI / Grok / Jimeng 默认复用 OpenAI Image API 形状，Gemini 走 `generateContent`
3. **内部多协议**：共享层内部支持 `/images/*`、`/chat/completions`、`generateContent`，但不把协议概念暴露给业务层
4. **先稳后扩**：当前不纳入 Responses API、多轮会话、流式 partial image、file_id 等高级能力

## 稳定对外 API

- `ProviderConfig`
- `GenerateRequest`
- `EditRequest`
- `ImageEditInput`
- `ImageResult`
- `ImageClient.generate_image()`
- `ImageClient.edit_image()`

## 快速开始

```python
from image_models import GenerateRequest, ImageClient, ImageProvider, ProviderConfig

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

## 支持的 Provider

| Provider | Generation | Edit | 默认协议 |
|----------|-----------|------|----------|
| openai | ✅ | ✅ | OpenAI Image API |
| grok | ✅ | ✅ | OpenAI-compatible Image API |
| jimeng | ✅ | ✅ | OpenAI-compatible Image API |
| gemini | ✅ | ✅ | Gemini generateContent |

## 内部协议切换

公共接口不暴露 protocol，但可以通过内部保留参数切换：

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
- `_protocol` 是共享层内部实现细节，不应在业务层大面积扩散
- 未显式指定时：`gemini -> generateContent`，其余默认走 `openai_images`
- `_protocol` 会在发请求前被剔除，不会透传给供应商接口

## mask 支持边界

- `openai_images` / 兼容 `/images/edits`：支持 `EditRequest.mask`
- `gemini_generate_content`：当前不显式使用 mask 字段，只支持输入参考图
- `openai_chat`：**当前不支持 mask**，会直接抛出错误，而不是做伪兼容

这样可以避免同一个 `EditRequest.mask` 在不同协议下产生不一致语义。

## 自动化接口文档

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

## 当前明确不做

- Responses API image tool
- `previous_response_id`
- 多轮图片会话
- partial image streaming
- file_id / files 上传抽象
- 视频生成抽象

## 供应商差异扩展点

虽然当前稳定接口只保留 `generate_image` / `edit_image`，但仍预留了两层扩展：

- `ProviderConfig.extra_params`：供应商级默认参数
- `GenerateRequest.extra_params` / `EditRequest.extra_params`：单次请求级参数

适用场景：
- Grok / Jimeng / OpenAI-compatible 在相同 `/images/*` 或 `/chat/completions` 接口上增加自定义字段
- 某些供应商对 `size` / `quality` / `response_format` 有额外约束或扩展参数

设计目标是：**稳定接口不变，差异通过 extra 参数下沉**。
