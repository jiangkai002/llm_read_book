import json
import logging
import sys
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s [LLM] %(message)s",
    force=True,
)
logger = logging.getLogger("llm_ask")

from auth.jwt_handler import get_current_user

llm_ask_router = APIRouter(prefix="/api/llm", tags=["LLM"])


class LLMAsk(BaseModel):
    book_name: str = Field(..., description="当前阅读的书籍名称")
    question: str = Field(..., description="用户提出的问题")
    image_base64: str = Field(
        ..., description="页面截图的 PNG Base64 编码（不含 data:image 前缀）")
    image_content: str = Field(..., description="截图对应的文字内容或 OCR 结果，辅助模型理解")
    api_key: str = Field(..., description="OpenAI 兼容 API 的密钥")
    base_url: str = Field(...,
                          description="API 根地址，例如 https://api.openai.com/v1")
    use_image: bool = Field(..., description="是否使用图片理解")
    model: str = Field(..., description="模型名称，可选支持 vision / 多模态")
    history_chat_list: list[str] = Field(..., description="历史聊天记录")


@llm_ask_router.post(
    "/llm_ask",
    summary="读书场景多模态问答（流式）",
    description=("根据书名、用户问题与页面截图调用多模态大模型，"
                 "以 SSE 流式格式返回 assistant 文本内容。"),
    response_description=
    "SSE 流：每帧格式为 data: {\"content\": \"...\"}，结束帧为 data: [DONE]",
)
async def llm_ask(
    payload: LLMAsk, _: str = Depends(get_current_user)) -> StreamingResponse:

    prompt = f"""
    你是一个专业的计算机领域的专家，现在用户正在阅读一本名为{payload.book_name}的书，用户现在遇到了一个问题，请你根据书中的内容以及用户的问题，给出详细的解答。
    用户问题是：
    {payload.question}
    请根据书中的内容，给出详细的解答。
    """

    # print("图片内容：", payload.image_base64)

    # api_key = os.getenv("api_key") if payload.api_key and payload.api_key != "" is None else payload.api_key
    # base_url = os.getenv("base_url") if payload.base_url and payload.base_url != "" is None else payload.base_url
    # model = os.getenv("llm_model") if payload.model and payload.model != "" is None else payload.model

    api_key = os.getenv("api_key")
    base_url = os.getenv("base_url")
    model = os.getenv("llm_model")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    # 解析历史消息，转换为 OpenAI messages 格式
    history_messages = []
    for item in payload.history_chat_list:
        try:
            msg = json.loads(item)
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                history_messages.append({"role": role, "content": content})
        except (json.JSONDecodeError, AttributeError):
            logger.warning("跳过无法解析的历史消息：%s", item)

    messages = history_messages + [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        },
    ]
    if payload.use_image:
        messages.append({
            "role":
            "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{payload.image_base64}"
                    },
                },
            ],
        })

    async def generate() -> AsyncIterator[str]:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        full_text: list[str] = []
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta is not None:
                full_text.append(delta)
                logger.debug(delta)
                yield f"data: {json.dumps({'content': delta}, ensure_ascii=False)}\n\n"
        logger.info("流式输出完成，完整内容：%s", "".join(full_text))
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
