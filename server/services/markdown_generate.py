"""根据本轮问答生成 / 追加本地 Markdown 笔记。

由大模型判断本轮笔记应当：
1. 追加（append）到现有的某个笔记文件中（主题强相关）；
2. 新建（create）一个新的笔记文件（主题不相关或没有合适的现有文件）。

服务以严格 JSON 形式返回决策与笔记内容，前端按字段处理。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger("markdown_generate")
_SKILL_FILE_PATH = Path(__file__).resolve().parent / "skills" / "markdown_generate" / "SKILL.md"

_SYSTEM_MESSAGE = (
    "你是一个本地笔记归档助手。用户正在阅读一本书，刚完成一轮问答。"
    "你的任务是将问答内容整理为结构化 Markdown 笔记，并判断应新建文件还是追加到已有文件。"
    "严格按用户指定的 JSON schema 输出，不要添加任何额外字段或说明文字。"
)

_MAX_CONTENT_CHARS = 6000  # ~2000 tokens for Chinese text
_MAX_IMAGE_CHARS = 2000


class ExistingNote(BaseModel):
    """现有本地笔记的轻量摘要，用于让模型判断是否归档到此处。"""

    filename: str
    summary: str = ""


class GenerateMarkdownRequest(BaseModel):
    book_name: str
    question: str
    answer: str
    image_content: str = ""
    existing_notes: list[ExistingNote] = []
    api_key: str
    base_url: str
    model: str


class GenerateMarkdownResult(BaseModel):
    action: str  # "create" 或 "append"
    target_filename: str
    title: str
    markdown: str
    reason: str = ""


# 模型偶尔会用代码块包裹 JSON，需要先剥掉再解析
_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$",
                            re.DOTALL | re.IGNORECASE)


def _strip_json_fence(text: str) -> str:
    m = _JSON_FENCE_RE.match(text.strip())
    return m.group(1) if m else text


def _truncate_content(text: str, max_chars: int = _MAX_CONTENT_CHARS) -> str:
    """Truncate overly long content to avoid prompt token overflow."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...(内容过长，已截断)"


def _build_existing_notes_block(notes: list[ExistingNote]) -> str:
    if not notes:
        return "（当前笔记目录为空，没有任何已有笔记。）"
    lines: list[str] = []
    for n in notes:
        summary = (n.summary or "").strip().replace("\n", " ")
        if len(summary) > 200:
            summary = summary[:200] + "..."
        lines.append(f"- {n.filename} -- {summary or '(无摘要)'}")
    return "\n".join(lines)


def _sanitize_filename(name: str) -> str:
    """模型给出的文件名可能含非法字符，做一次清理并保证 .md 后缀。"""
    name = (name or "").strip().strip("\"'")
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]", "", name)
    if not name:
        name = datetime.now().strftime("%Y-%m-%d-note")
    if not (name.endswith(".md") or name.endswith(".markdown")):
        name += ".md"
    return name


def _fallback_filename(question: str) -> str:
    base = (question or "note").strip().replace("\n", " ")
    base = re.sub(r"[\\/:*?\"<>|\r\n\t]", "", base)
    base = base[:20].strip() or "note"
    return f"{datetime.now().strftime('%Y-%m-%d')}-{base}.md"


def _build_prompt(req: GenerateMarkdownRequest) -> str:
    existing_block = _build_existing_notes_block(req.existing_notes)
    image_block = _truncate_content(req.image_content.strip(), _MAX_IMAGE_CHARS) or "（无）"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    skill_template = _load_skill_template()
    return skill_template.format(
        book_name=req.book_name,
        question=_truncate_content(req.question),
        answer=_truncate_content(req.answer),
        image_content=image_block,
        existing_notes=existing_block,
        current_time=current_time,
    )


_MINIMAL_FALLBACK_TEMPLATE = (
    "将以下问答整理为 Markdown 笔记，判断新建(create)还是追加(append)到现有文件。\n"
    "问题：{question}\n回答：{answer}\n截图内容：{image_content}\n"
    "现有笔记：{existing_notes}\n当前时间：{current_time}\n"
    "输出 JSON: {{\"action\":\"create|append\","
    "\"target_filename\":\"...\",\"title\":\"...\","
    "\"markdown\":\"...\",\"reason\":\"...\"}}"
)


def _load_skill_template() -> str:
    """读取 SKILL.md 作为 prompt 模板，不存在时回退最小模板。"""
    try:
        return _SKILL_FILE_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.warning("未找到 SKILL.md，使用最小内置 prompt 模板：%s", _SKILL_FILE_PATH)
        return _MINIMAL_FALLBACK_TEMPLATE


async def generate_or_append_note(
        req: GenerateMarkdownRequest) -> GenerateMarkdownResult:
    """调用 LLM 生成笔记并判断 create/append。"""

    client = AsyncOpenAI(api_key=req.api_key, base_url=req.base_url)
    prompt = _build_prompt(req)
    logger.debug("markdown_generate prompt:\n%s", prompt)

    completion = await client.chat.completions.create(
        model=req.model,
        messages=[
            {"role": "system", "content": _SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=2048,
    )

    # Token 使用日志
    usage = completion.usage
    if usage:
        logger.info(
            "markdown_generate tokens: prompt=%d, completion=%d, total=%d",
            usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
        )

    raw = completion.choices[0].message.content or "{}"
    logger.debug("markdown_generate raw output: %s", raw)

    try:
        data: dict[str, Any] = json.loads(_strip_json_fence(raw))
    except json.JSONDecodeError:
        logger.warning("无法解析模型 JSON 输出，回退为 create 模式：%s", raw)
        data = {}

    action = (data.get("action") or "").strip().lower()
    if action not in ("create", "append"):
        action = "create"

    target_filename = _sanitize_filename(
        str(data.get("target_filename") or ""))

    existing_filenames = {n.filename for n in req.existing_notes}
    if action == "append" and target_filename not in existing_filenames:
        # 模型说要 append，但给出的文件名不在现有列表里，降级为 create
        logger.warning("模型返回 append，但 target_filename 不在现有列表中：%s -> 降级为 create",
                       target_filename)
        action = "create"

    if action == "create" and (not target_filename
                               or target_filename in existing_filenames):
        # create 时若文件名为空 / 与现有重名，回退到一个安全的默认名
        target_filename = _fallback_filename(req.question)
        # 若仍然重名，加时间戳后缀
        if target_filename in existing_filenames:
            stem = target_filename[:-3]
            target_filename = f"{stem}-{datetime.now().strftime('%H%M%S')}.md"

    title = (data.get("title") or req.question or "AI 笔记").strip()
    markdown = (data.get("markdown") or "").strip()

    if not markdown:
        # 兜底：直接使用原始 answer，避免空文件
        if action == "append":
            markdown = (f"\n\n---\n\n## {title}\n\n{req.answer.strip()}\n\n"
                        f"> 提问：{req.question.strip()}\n\n"
                        f"*记于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
        else:
            markdown = (f"# {title}\n\n## {title}\n\n{req.answer.strip()}\n\n"
                        f"> 提问：{req.question.strip()}\n\n"
                        f"*记于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    reason = str(data.get("reason") or "").strip()
    if not reason:
        reason = f"自动选择{action}模式"

    return GenerateMarkdownResult(
        action=action,
        target_filename=target_filename,
        title=title,
        markdown=markdown,
        reason=reason,
    )