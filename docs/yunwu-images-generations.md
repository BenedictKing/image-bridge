## 创建 gpt-image-2

POST

https://yunwu.ai/v1/images/generations

给定一个提示，该模型将返回一个或多个预测的完成，并且还可以返回每个位置的替代标记的概率。

为提供的提示和参数创建完成

官方文档： [https://platform.openai.com/docs/api-reference/images/create](https://platform.openai.com/docs/api-reference/images/create)

## 请求参数

model

string

模型名

必需

prompt

string

必需

所需图像的文本描述。最大长度为 1000 个字符。

size

string

可选

图片尺寸  
1024x1024 正方形  
1536x1024 横版  
1024x1536 竖版  
2048x2048 2K正方形  
2048x1152 2K横版  
3840x2160 4K横版  
2160x3840 4K竖版  
auto 默认

尺寸严格限制规则

1.

图片最大边长 ≤ 3840px

2.

宽高两边像素均为 16px 的倍数

3.

长边 / 短边 比值 ≤ 3:1

4.

总像素范围：最小 655360 ~ 最大 8294400

format

string

可选

图片格式  
可选：png 、 jpeg 、 webp

quality

string

可选

图片画质  
可选：low 、 medium 、 high 、 auto（默认）

n

integer

必需

要生成的图像数。必须介于 1 和 10 之间。

```
{
    "model": "gpt-image-2",
    "prompt": "A childrens book drawing of a veterinarian using a stethoscope to listen to the heartbeat of a baby otter.",
    "n": 1,
    "size": "1024x1024",
    "quality": "low",
    "format": "jpeg"
}
```

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

修改于 4 天前
