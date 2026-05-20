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
from typing import Any, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger("markdown_generate")


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


# 模型偶尔会用代码块包裹 JSON，需要先剥掉再解析
_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL | re.IGNORECASE
)


def _strip_json_fence(text: str) -> str:
    m = _JSON_FENCE_RE.match(text.strip())
    return m.group(1) if m else text


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
    image_block = req.image_content.strip() or "（无）"

    # 如果用户指定了要追加到哪个笔记，把该笔记的完整内容也传进去
    existing_content_block = ""
    if req.existing_note_filename and req.existing_note_content is not None:
        content = req.existing_note_content.strip()
        if content:
            existing_content_block = f"\n\n【用户选定的目标笔记 {req.existing_note_filename} 的现有内容】\n{content}\n"

    return f"""你是一个智能的本地笔记归档助手。用户在阅读《{req.book_name}》时，向 AI 助手提出了一个问题，并得到了回答。
现在请你将本轮问答整理成一段简洁、结构化的 Markdown 笔记，并判断这段笔记应当：
- 追加（append）到下面"现有笔记列表"中的某一个文件中（仅当主题/知识点高度相关时）；或
- 新建（create）一个新的 Markdown 文件（当现有笔记中找不到主题相关的归宿时）。

【用户的问题】
{req.question}

【AI 助手的回答】
{req.answer}

【截图相关的文字 / OCR 内容】
{image_block}
{existing_content_block}
【现有笔记列表（文件名 -- 摘要）】
{existing_block}

请按以下规则整理 Markdown 内容（字段 markdown）：
1. 以一个 ## 开头的小节标题概括本次知识点；
2. 用列表 / 加粗 / 行内代码 / 公式等方式条理化地总结回答；不要冗长复述用户原文；
3. 尾部加一行 `> 提问：xxx` 引用原始问题，再加一行斜体的提问时间，例如 `*记于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*`；
4. 如果是 append，markdown 字段开头加一条 `\\n\\n---\\n\\n` 分隔线，便于追加后视觉分隔；如果是 create，则不要添加这条分隔线，并以一个 `# 标题` 作为整篇笔记的一级标题开头。

请严格、并且仅输出如下结构的 JSON（不要使用 Markdown 代码块包裹，不要附带其它文字）：
{{
  "action": "create" 或 "append",
  "target_filename": "若 append 必须是上方现有笔记列表中的某个文件名；若 create 则给出一个新文件名（必须以 .md 结尾，文件名不要包含 / \\\\ : * ? \\" < > | 等非法字符，使用中文或英文均可）",
  "title": "笔记小节标题（不含 # 号）",
  "markdown": "要写入文件的 Markdown 内容（按上述规则）",
  "reason": "简短说明你为什么选择 create 或 append"
}}
"""


async def generate_or_append_note(
    req: GenerateMarkdownRequest,
) -> GenerateMarkdownResult:
    """调用 LLM 生成笔记并判断 create/append。"""

    is_debug = os.getenv("is_debug", "false").strip().lower() == "true"
    if is_debug:
        req.api_key = os.getenv("api_key", "")
        req.base_url = os.getenv("base_url", "")
        req.model = os.getenv("llm_model", "")
    client = AsyncOpenAI(api_key=req.api_key, base_url=req.base_url)

    # 如果用户明确选择了某个笔记，直接追加到该笔记
    if req.existing_note_filename and req.existing_note_filename.strip():
        target_filename = _sanitize_filename(req.existing_note_filename)

        # 使用简化的 prompt，只生成要追加的内容
        append_prompt = f"""你是一个笔记整理助手。用户在阅读《{req.book_name}》时，向 AI 助手提出了一个问题并得到了回答。
请将下面的问答整理成一段简洁、结构化的 Markdown 内容。

【用户的问题】
{req.question}

【AI 助手的回答】
{req.answer}

请按以下规则整理 Markdown 内容：
1. 以一个 ## 开头的小节标题概括本次知识点；
2. 用列表 / 加粗 / 行内代码 / 公式等方式条理化地总结回答；
3. 尾部加一行 `> 提问：xxx` 引用原始问题，再加一行斜体的提问时间，例如 `*记于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*`；
4. 开头加一条 `\\n\\n---\\n\\n` 分隔线。

请严格、并且仅输出如下结构的 JSON（不要使用 Markdown 代码块包裹，不要附带其它文字）：
{{
  "title": "笔记小节标题（不含 # 号）",
  "markdown": "要追加的 Markdown 内容（按上述规则，开头有分隔线）"
}}
"""

        completion = await client.chat.completions.create(
            model=req.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个严谨的助手，必须按用户要求只输出 JSON 对象，不要附加任何说明文字、不要使用 Markdown 代码块包裹。",
                },
                {
                    "role": "user",
                    "content": append_prompt,
                },
            ],
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content or "{}"
        logger.debug("markdown_generate append raw output: %s", raw)

        try:
            data: dict[str, Any] = json.loads(_strip_json_fence(raw))
        except json.JSONDecodeError:
            logger.warning("无法解析模型 JSON 输出，使用兜底内容：%s", raw)
            data = {}

        title = (data.get("title") or req.question or "AI 笔记").strip()
        markdown = (data.get("markdown") or "").strip()

        if not markdown:
            markdown = (
                f"\n\n---\n\n## {title}\n\n{req.answer.strip()}\n\n"
                f"> 提问：{req.question.strip()}\n\n"
                f"*记于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
            )

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

    completion = await client.chat.completions.create(
        model=req.model,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个严谨的助手，必须按用户要求只输出 JSON 对象，不要附加任何说明文字、不要使用 Markdown 代码块包裹。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
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

    target_filename = _sanitize_filename(str(data.get("target_filename") or ""))

    existing_filenames = {n.filename for n in req.existing_notes}
    if action == "append" and target_filename not in existing_filenames:
        # 模型说要 append，但给出的文件名不在现有列表里，降级为 create
        logger.warning(
            "模型返回 append，但 target_filename 不在现有列表中：%s -> 降级为 create",
            target_filename,
        )
        action = "create"

    if action == "create" and (
        not target_filename or target_filename in existing_filenames
    ):
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

    reason = str(data.get("reason") or "").strip()

    return GenerateMarkdownResult(
        action=action,
        target_filename=target_filename,
        title=title,
        markdown=markdown,
        reason=reason,
    )
