## 编辑 gpt-image-2

POST

https://yunwu.ai/v1/images/edits

给定一个提示，该模型将返回一个或多个预测的完成，并且还可以返回每个位置的替代标记的概率。

为提供的提示和参数创建完成

官方文档： [https://platform.openai.com/docs/api-reference/images/createEdit](https://platform.openai.com/docs/api-reference/images/createEdit)

## 请求参数

image

file

必需

要编辑的图片。必须是受支持的图片文件或图片数组。对于 gpt-image-1，每张图片应为小于 25MB 的 png、webp 或 jpg 文件。对于 dall-e-2，您只能提供一张图片，并且该图片应为小于 4MB 的方形 png 文件。

示例:

\["file://C:\\\\Users\\\\Administrator\\\\Desktop\\\\例子.png","file://C:\\\\Users\\\\Administrator\\\\Desktop\\\\场景2.png"\]

prompt

string

必需

所需图像的文本描述。dall-e-2 的最大长度为 1000 个字符，gpt-image-1 的最大长度为 32000 个字符。

示例:

将他们合并在一个图片里面

mask

string

可选

一张附加图片，其完全透明区域（例如，alpha 值为零）指示应编辑 image 位置。如果提供了多张图片，则遮罩将应用于第一张图片。必须是有效的 PNG 文件，小于 4MB，且尺寸与 image 相同。

model

string

可选

用于生成图像的模型。仅 gpt-image-1, gpt-image-1-all, flux-kontext-pro, flux-kontext-max,gpt-image-2,gpt-image-2-all

示例:

gpt-image-2-all

n

string

可选

要生成的图像数量。必须介于 1 到 10 之间。

示例:

1

quality

string

可选

生成图像的质量。只有 gpt-image-1 支持 high、medium 和 low 质量。dall-e-2 仅支持 standard 质量。默认为 auto。

response\_format

string

可选

返回生成图像的格式。必须是 url 或 b64\_json 之一。URL 在图像生成后 60 分钟内有效。此参数仅适用于 dall-e-2，因为 gpt-image-1 始终返回 base64 编码的图像，请不要使用这个参数。

示例:

url

size

string

可选

生成图像的尺寸。对于 GPT 图像模型，必须是 1024x1024 、 1536x1024 （横版）、 1024x1536 （竖版）或 auto （默认值）之一，对于 dall-e-2 必须是 256x256 、 512x512 或 1024x1024 之一，对于 dall-e-3 必须是 1024x1024 、 1792x1024 或 1024x1792 之一。

示例:

1024x1536

background

string

可选

允许为生成的图像的背景设置透明度。此参数仅在 gpt-image-1 中受支持。其值必须为 “透明（transparent）”、“不透明（opaque）” 或 “自动（auto）”（默认值）之一。当使用 “自动（auto）” 时，模型将自动为图像确定最佳背景。

示例:

transparent

moderation

string

可选

控制由 gpt-image-1 生成的图像的内容审核级别。可以设置为 “low” 以进行限制较少的过滤，也可以设置为 “auto”（默认值）。

示例:

low

## 请求示例代码

## 返回响应

🟢200OK

application/json

Body

id

string

必需

object

string

必需

created

integer

必需

choices

array \[object\]

必需

index

integer

可选

message

object

可选

finish\_reason

string

可选

usage

object

必需

prompt\_tokens

integer

必需

completion\_tokens

integer

必需

total\_tokens

integer

必需

```
{
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677652288,
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "\n\nHello there, how may I assist you today?"
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 9,
        "completion_tokens": 12,
        "total_tokens": 21
    }
}
```

修改于 3 天前
