"""Shared Pydantic AI helpers for OpenAI-compatible models."""

from __future__ import annotations

import base64
import json
from typing import Any, Optional

from pydantic_ai import Agent
from pydantic_ai.messages import (
    BinaryContent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


def build_openai_model(
    *,
    api_key: str,
    base_url: Optional[str],
    model_name: str,
) -> OpenAIChatModel:
    provider = OpenAIProvider(api_key=api_key or None, base_url=base_url or None)
    return OpenAIChatModel(model_name=model_name, provider=provider)


def build_agent(
    *,
    api_key: str,
    base_url: Optional[str],
    model_name: str,
    system_prompt: Optional[str] = None,
    output_type: Any = str,
) -> Agent[Any, Any]:
    return Agent(
        build_openai_model(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
        ),
        system_prompt=system_prompt,
        output_type=output_type,
    )


def parse_history_messages(history_chat_list: list[str]) -> list[ModelMessage]:
    """Convert the frontend's serialized chat history into Pydantic AI history."""
    messages: list[ModelMessage] = []

    for item in history_chat_list:
        try:
            msg = json.loads(item)
        except (json.JSONDecodeError, TypeError):
            continue

        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        if role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
        elif role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))

    return messages


def png_base64_content(image_base64: str) -> BinaryContent:
    """Build a PNG content part from a plain base64 payload."""
    return BinaryContent(
        data=base64.b64decode(image_base64),
        media_type="image/png",
    )
