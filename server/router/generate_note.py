import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from auth.jwt_handler import get_current_user
from services.llm_agent import build_agent
from services.markdown_generate import (
    ExistingNote,
    GenerateMarkdownRequest,
    GenerateMarkdownResult,
    generate_or_append_note,
)

load_dotenv()

logger = logging.getLogger("generate_note")

generate_note_router = APIRouter(prefix="/api/generate_note",
                                 tags=["Generate Note"])


class GenerateNote(BaseModel):
    book_name: str
    question: str
    history_chat_list: list[str]
    api_key: str
    base_url: str
    model: str
    images: list[str]


@generate_note_router.post("/generate_note",
                           summary="生成笔记",
                           description="根据书名、用户问题、历史聊天记录、图片生成笔记")
async def generate_note(
    generate_note: GenerateNote, _: str = Depends(get_current_user)
) -> Optional[str]:
    prompt = f"你是{generate_note.book_name}的阅读助手，用户遇到一个问题进行了询问，并想根据书的内容进行笔记的生成。"
    prompt += f"用户的问题是：{generate_note.question}"
    prompt += f"用户的历史聊天记录是：{generate_note.history_chat_list}"
    prompt += f"用户提供的图片是：{generate_note.images}"
    prompt += f"请根据书的内容，给出详细的笔记。"
    prompt += f"请注意，笔记的格式必须为markdown格式。"

    agent = build_agent(
        api_key=generate_note.api_key,
        base_url=generate_note.base_url,
        model_name=generate_note.model,
    )
    result = await agent.run(prompt)
    return result.output


class GenerateOrAppendRequest(BaseModel):
    """前端把本轮问答 + 现有笔记摘要传上来，由后端调用 LLM 决策。"""

    book_name: str = Field(..., description="当前阅读的书籍名称")
    question: str = Field(..., description="本轮用户的问题")
    answer: str = Field(..., description="本轮 AI 助手的完整回答")
    image_content: str = Field("", description="截图对应文字 / OCR / 选区文本，可为空")
    existing_notes: list[ExistingNote] = Field(
        default_factory=list, description="本地笔记目录现有 .md 文件的文件名 + 摘要")
    # 当用户选择了某个具体笔记时，传入该笔记的完整内容
    existing_note_filename: Optional[str] = Field(None, description="用户选择的已有笔记文件名")
    existing_note_content: Optional[str] = Field(None, description="用户选择的已有笔记的完整内容")
    api_key: str = Field("", description="OpenAI 兼容 API Key，留空则使用服务端 .env 中的默认值")
    base_url: str = Field("", description="OpenAI 兼容 API 根地址")
    model: str = Field("", description="模型名称")


@generate_note_router.post( 
    "/generate_or_append",
    summary="把本轮问答整理成 markdown 笔记，并由 LLM 判定 create/append",
    description=("根据本轮 question + answer + 截图上下文，让大模型判断这次笔记应当：\n"
                 "- 追加到现有的某个本地笔记中（append），或\n"
                 "- 新建一个新的本地笔记文件（create）。\n\n"
                 "返回结构化结果，前端按字段写入文件系统。"),
    response_model=GenerateMarkdownResult,
)
async def generate_or_append(
    payload: GenerateOrAppendRequest,
    _: str = Depends(get_current_user),
) -> GenerateMarkdownResult:
    api_key = payload.api_key.strip() or os.getenv("api_key", "")
    base_url = payload.base_url.strip() or os.getenv("base_url", "")
    model = payload.model.strip() or os.getenv("llm_model", "")

    req = GenerateMarkdownRequest(
        book_name=payload.book_name or "当前书籍",
        question=payload.question,
        answer=payload.answer,
        image_content=payload.image_content,
        existing_notes=payload.existing_notes,
        existing_note_filename=payload.existing_note_filename,
        existing_note_content=payload.existing_note_content,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    result = await generate_or_append_note(req)
    logger.info("generate_or_append -> action=%s, file=%s, reason=%s",
                result.action, result.target_filename, result.reason)
    return result
