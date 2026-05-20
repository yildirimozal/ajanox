"""Tool-call parsing.

Ajanox model-agnostic bir protokol kullanır: LLM çıktısı içinden
<tool_call>{...}</tool_call> bloklarını çıkarır. Ollama'nın native
tool API'sine bağlı değildir; farklı modellerle aynı kod çalışır.
"""

from __future__ import annotations

import json
import re
from typing import Optional, TypedDict


class ToolCall(TypedDict):
    name: str
    arguments: dict


_TAG_PATTERN = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL
)
_RAW_JSON_PATTERN = re.compile(
    r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^{}]*\}\s*\}',
    re.DOTALL,
)


def extract_tool_call(content: str) -> Optional[ToolCall]:
    """LLM cevabından bir tool çağrısı varsa parse et, yoksa None.

    İki format desteklenir:
      1. <tool_call>{json}</tool_call> — Qwen ve birçok model için kanonik
      2. Düz {"name": ..., "arguments": ...} — fallback
    """
    if not content:
        return None

    match = _TAG_PATTERN.search(content)
    if match:
        try:
            data = json.loads(match.group(1))
            if _is_valid_tool_call(data):
                return data  # type: ignore[return-value]
        except json.JSONDecodeError:
            pass

    match = _RAW_JSON_PATTERN.search(content)
    if match:
        try:
            data = json.loads(match.group(0))
            if _is_valid_tool_call(data):
                return data  # type: ignore[return-value]
        except json.JSONDecodeError:
            return None

    return None


def _is_valid_tool_call(data: object) -> bool:
    return (
        isinstance(data, dict)
        and isinstance(data.get("name"), str)
        and isinstance(data.get("arguments"), dict)
    )


def strip_tool_call_tags(content: str) -> str:
    """Final yanıtta artık tool_call etiketi varsa temizle."""
    return re.sub(r"</?tool_call>", "", content).strip()
