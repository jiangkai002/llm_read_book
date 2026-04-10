from fastapi import APIRouter
from pydantic import BaseModel
from openai import AsyncOpenAI

llm_ask_router = APIRouter(prefix="/llm")


class LLMAsk(BaseModel):
    book_name: str
    question: str
    image_base64: str
    image_content:str
    api_key: str
    base_url: str
    model: str


@llm_ask_router.post("/llm_ask")
async def llm_ask(llm_ask: LLMAsk):

    prompt = f"""
    你是一个专业的计算机领域的专家，现在用户正在阅读一本名为{llm_ask.book_name}的书，用户现在遇到了一个问题，请你根据书中的内容以及用户的问题，给出详细的解答。
    用户问题是：
    {llm_ask.question}
    提问的书本截图的内容是：
    {llm_ask.image_content}
    请根据书中的内容，给出详细的解答。
    """

    client = AsyncOpenAI(
        api_key=llm_ask.api_key,
        base_url=llm_ask.base_url,
    )
    completion = await client.chat.completions.create(
        model=llm_ask.model,
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
