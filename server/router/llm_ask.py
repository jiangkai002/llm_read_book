from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from openai import AsyncOpenAI

llm_ask_router = APIRouter(prefix="/api/llm", tags=["LLM"])


class LLMAsk(BaseModel):
    book_name: str = Field(..., description="当前阅读的书籍名称")
    question: str = Field(..., description="用户提出的问题")
    image_base64: str = Field(..., description="页面截图的 PNG Base64 编码（不含 data:image 前缀）")
    image_content: str = Field(..., description="截图对应的文字内容或 OCR 结果，辅助模型理解")
    api_key: str = Field(..., description="OpenAI 兼容 API 的密钥")
    base_url: str = Field(..., description="API 根地址，例如 https://api.openai.com/v1")
    model: str = Field(..., description="模型名称，可选支持 vision / 多模态")


@llm_ask_router.post(
    "/llm_ask",
    summary="读书场景多模态问答",
    description=(
        "根据书名、用户问题与页面截图调用多模态大模型，"
        "结合截图中的书本内容给出解答。请求体为 OpenAI 兼容服务的连接参数与上下文。"
    ),
    response_description="模型返回的 assistant 文本内容",
)
async def llm_ask(payload: LLMAsk) -> Optional[str]:

    prompt = f"""
    你是一个专业的计算机领域的专家，现在用户正在阅读一本名为{payload.book_name}的书，用户现在遇到了一个问题，请你根据书中的内容以及用户的问题，给出详细的解答。
    用户问题是：
    {payload.question}
    提问的书本截图的内容是：
    {payload.image_content}
    请根据书中的内容，给出详细的解答。
    """

    client = AsyncOpenAI(
        api_key=payload.api_key,
        base_url=payload.base_url,
    )
    completion = await client.chat.completions.create(
        model=payload.model,
        messages=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": "You are a Professional experts."}
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{payload.image_base64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            },
        ],
    )
    return completion.choices[0].message.content
