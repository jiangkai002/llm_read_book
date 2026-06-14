"""根据本轮问答生成 / 追加本地 Markdown 笔记。

由大模型判断本轮笔记应当：
1. 追加（append）到现有的某个笔记文件中（主题强相关）；
2. 新建（create）一个新的笔记文件（主题不相关或没有合适的现有文件）。

服务以严格 JSON 形式返回决策与笔记内容，前端按字段处理。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

from services.llm_agent import build_agent

load_dotenv()

logger = logging.getLogger("markdown_generate")
_SKILL_FILE_PATH = Path(__file__).resolve().parent / "skills" / "markdown_generate" / "SKILL.md"

_FALLBACK_SKILL_TEMPLATE = (
    "你是一个本地笔记归档助手。用户正在阅读《{book_name}》，刚完成一轮问答。"
    "请将问答内容整理为结构化 Markdown 笔记，并判断应新建文件还是追加到已有文件。\n\n"
    "用户问题：{question}\n\n"
    "AI 回答：{answer}\n\n"
    "截图 / OCR 内容：{image_content}\n\n"
    "现有笔记列表：\n{existing_notes}\n\n"
    "当前时间：{current_time}\n\n"
    "严格输出 action、target_filename、title、markdown、reason 字段。"
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
    existing_notes: list[ExistingNote] = Field(default_factory=list)
    # 当用户选择了某个具体笔记时，传入该笔记的完整内容
    existing_note_filename: Optional[str] = None
    existing_note_content: Optional[str] = None
    api_key: str
    base_url: str
    model: str


class GenerateMarkdownResult(BaseModel):
    action: str  # "create" 或 "append"
    target_filename: str
    title: str
    markdown: str
    reason: str = ""


def _truncate_content(text: str, max_chars: int = _MAX_CONTENT_CHARS) -> str:
    """Truncate overly long content to avoid prompt token overflow."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...(内容过长，已截断)"


def _load_skill_template() -> str:
    """Read the local markdown generation skill so prompt rules live outside code."""
    try:
        return _SKILL_FILE_PATH.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("无法读取 markdown_generate skill，使用内置兜底提示词：%s", exc)
        return _FALLBACK_SKILL_TEMPLATE


def _render_skill_template(
    *,
    book_name: str,
    question: str,
    answer: str,
    image_content: str,
    existing_notes: str,
    current_time: str,
) -> str:
    # SKILL.md contains JSON examples, so avoid str.format and only replace known placeholders.
    prompt = _load_skill_template()
    replacements = {
        "{book_name}": book_name,
        "{question}": question,
        "{answer}": answer,
        "{image_content}": image_content,
        "{existing_notes}": existing_notes,
        "{current_time}": current_time,
    }
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt


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


def _sanitize_new_filename(name: str) -> str:
    """Sanitize a model-proposed new file name and keep it at the notes root."""
    name = (name or "").strip().strip("\"'")
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]", "", name)
    if not name:
        name = datetime.now().strftime("%Y-%m-%d-note")
    if not (name.endswith(".md") or name.endswith(".markdown")):
        name += ".md"
    return name


def _normalize_existing_filename(name: str) -> str:
    """Normalize an existing note identifier while preserving relative directories."""
    name = (name or "").strip().strip("\"'").replace("\\", "/")
    parts = [
        re.sub(r"[\\:*?\"<>|\r\n\t]", "", part).strip()
        for part in name.split("/")
        if part.strip() and part.strip() not in (".", "..")
    ]
    return "/".join(parts)


def _resolve_existing_filename(name: str, existing_filenames: set[str]) -> Optional[str]:
    """Resolve exact path first, then a unique basename for backward compatibility."""
    normalized = _normalize_existing_filename(name)
    if normalized in existing_filenames:
        return normalized

    basename_matches = [
        filename for filename in existing_filenames if Path(filename).name == Path(normalized).name
    ]
    if len(basename_matches) == 1:
        return basename_matches[0]
    return None


def _fallback_filename(question: str) -> str:
    base = (question or "note").strip().replace("\n", " ")
    base = re.sub(r"[\\/:*?\"<>|\r\n\t]", "", base)
    base = base[:20].strip() or "note"
    return f"{datetime.now().strftime('%Y-%m-%d')}-{base}.md"


def _build_prompt(req: GenerateMarkdownRequest) -> str:
    existing_block = _build_existing_notes_block(req.existing_notes)
    image_block = _truncate_content(req.image_content, _MAX_IMAGE_CHARS) or "（无）"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 如果用户指定了要追加到哪个笔记，把该笔记的完整内容也传进去
    existing_content_block = ""
    if req.existing_note_filename and req.existing_note_content is not None:
        content = _truncate_content(req.existing_note_content)
        if content:
            existing_content_block = (
                f"\n\n# 补充上下文\n\n"
                f"用户选定的目标笔记 `{req.existing_note_filename}` 当前内容如下：\n\n{content}\n"
            )

    return (
        _render_skill_template(
            book_name=req.book_name,
            question=req.question,
            answer=_truncate_content(req.answer),
            image_content=image_block,
            existing_notes=existing_block,
            current_time=current_time,
        )
        + existing_content_block
    )


async def generate_or_append_note(
    req: GenerateMarkdownRequest,
) -> GenerateMarkdownResult:
    """调用 LLM 生成笔记并判断 create/append。"""

    is_debug = os.getenv("is_debug", "false").strip().lower() == "true"
    if is_debug:
        req.api_key = os.getenv("api_key", "")
        req.base_url = os.getenv("base_url", "")
        req.model = os.getenv("llm_model", "")
    # 如果用户明确选择了某个笔记，直接追加到该笔记
    if req.existing_note_filename and req.existing_note_filename.strip():
        target_filename = _normalize_existing_filename(req.existing_note_filename)

        append_prompt = (
            _build_prompt(req)
            + "\n\n# 强制归档约束\n\n"
            + f"用户已经明确选择目标笔记 `{target_filename}`。"
            + "本次必须返回 `action: append`，`target_filename` 必须完全等于该文件名，"
            + "markdown 必须以 `\\n\\n---\\n\\n` 开头，且不要生成一级标题。"
        )

        agent = build_agent(
            api_key=req.api_key,
            base_url=req.base_url,
            model_name=req.model,
            system_prompt="你是一个严谨的助手，必须按用户要求输出结构化结果。",
            output_type=GenerateMarkdownResult,
        )
        result = await agent.run(append_prompt)

        title = (result.output.title or req.question or "AI 笔记").strip()
        markdown = (result.output.markdown or "").rstrip()

        if not markdown.strip():
            markdown = (
                f"\n\n---\n\n## {title}\n\n{req.answer.strip()}\n\n"
                f"> 提问：{req.question.strip()}\n\n"
                f"*记于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
            )
        elif not markdown.startswith("\n\n---\n\n"):
            markdown = "\n\n---\n\n" + markdown.lstrip()

        return GenerateMarkdownResult(
            action="append",
            target_filename=target_filename,
            title=title,
            markdown=markdown,
            reason=f"用户明确选择追加到 {target_filename}",
        )

    # 没有指定笔记，让 LLM 决定
    prompt = _build_prompt(req)
    logger.debug("markdown_generate prompt:\n%s", prompt)

    agent = build_agent(
        api_key=req.api_key,
        base_url=req.base_url,
        model_name=req.model,
        system_prompt=(
            "你是一个严谨的助手，必须按用户要求输出结构化结果。"
            "不要附加任何说明文字、不要使用 Markdown 代码块包裹。"
        ),
        output_type=GenerateMarkdownResult,
    )
    result = await agent.run(prompt)
    data = result.output

    action = (data.action or "").strip().lower()
    if action not in ("create", "append"):
        action = "create"

    existing_filenames = {n.filename for n in req.existing_notes}
    if action == "append":
        resolved = _resolve_existing_filename(data.target_filename, existing_filenames)
        if resolved:
            target_filename = resolved
        else:
            target_filename = _sanitize_new_filename(data.target_filename)
            # 模型说要 append，但给出的文件名不在现有列表里，降级为 create
            logger.warning(
                "模型返回 append，但 target_filename 不在现有列表中：%s -> 降级为 create",
                data.target_filename,
            )
            action = "create"
    else:
        target_filename = _sanitize_new_filename(data.target_filename)

    if action == "create" and (
        not target_filename or target_filename in existing_filenames
    ):
        # create 时若文件名为空 / 与现有重名，回退到一个安全的默认名
        target_filename = _fallback_filename(req.question)
        # 若仍然重名，加时间戳后缀
        if target_filename in existing_filenames:
            stem = target_filename[:-3]
            target_filename = f"{stem}-{datetime.now().strftime('%H%M%S')}.md"

    title = (data.title or req.question or "AI 笔记").strip()
    markdown = (data.markdown or "").rstrip()

    if not markdown.strip():
        # 兜底：直接使用原始 answer，避免空文件
        if action == "append":
            markdown = (
                f"\n\n---\n\n## {title}\n\n{req.answer.strip()}\n\n"
                f"> 提问：{req.question.strip()}\n\n"
                f"*记于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
            )
        else:
            markdown = (
                f"# {title}\n\n## {title}\n\n{req.answer.strip()}\n\n"
                f"> 提问：{req.question.strip()}\n\n"
                f"*记于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
            )
    elif action == "append" and not markdown.startswith("\n\n---\n\n"):
        markdown = "\n\n---\n\n" + markdown.lstrip()

    reason = (data.reason or "").strip()
    if not reason:
        reason = f"自动选择{action}模式"

    return GenerateMarkdownResult(
        action=action,
        target_filename=target_filename,
        title=title,
        markdown=markdown,
        reason=reason,
    )
