from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from openai import AsyncOpenAI
import json

generate_note_router = APIRouter(prefix="/generate_note")


class GenerateNote(BaseModel):
    book_name: str
    question: str
    history_chat_list: list[str]
    api_key: str
    base_url: str
    model: str
    images: list[str]


@generate_note_router.post("/generate_note")
async def generate_note(generate_note: GenerateNote) -> Optional[str]:
    prompt = f"你是{generate_note.book_name}的阅读助手，用户遇到一个问题进行了询问，并想根据书的内容进行笔记的生成。"
    prompt += f"用户的问题是：{generate_note.question}"
    prompt += f"用户的历史聊天记录是：{generate_note.history_chat_list}"
    prompt += f"用户提供的图片是：{generate_note.images}"
    prompt += f"请根据书的内容，给出详细的笔记。"
    prompt += f"请注意，笔记的格式必须为markdown格式。"

    client = AsyncOpenAI(
        api_key=generate_note.api_key,
        base_url=generate_note.base_url,
    )
    messages = [
        {
            "role": "user",
            "content": prompt,
        },
    ]
    completion = await client.chat.completions.create(
        model=generate_note.model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    return completion.choices[0].message.content
