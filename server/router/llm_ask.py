from fastapi import APIRouter
from pydantic import BaseModel
from openai import AsyncOpenAI
from config import config

llm_ask_router = APIRouter(prefix="/llm")


class LLMAsk(BaseModel):
    book_name: str
    question: str
    image_base64: str


@llm_ask_router.post("/llm_ask")
async def llm_ask(llm_ask: LLMAsk):

    prompt = f"""
    你是一个专业的计算机领域的专家，现在用户正在阅读一本名为{llm_ask.book_name}的书，用户现在遇到了一个问题，请你根据书中的内容以及用户的问题，给出详细的解答。
    用户问题是：
    {llm_ask.question}
    请根据书中的内容，给出详细的解答。
    """

    client = AsyncOpenAI(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
        api_key=config.api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    completion = await client.chat.completions.create(
        model="qwen-vl-max-latest",
        messages=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": "You are a Professional computer experts."}
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{llm_ask.image_base64}"
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
