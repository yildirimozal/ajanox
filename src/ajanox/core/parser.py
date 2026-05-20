"""Tool-call parsing.

Ajanox model-agnostic bir protokol kullanır: LLM çıktısı içinden
<tool_call>{...}</tool_call> bloklarını çıkarır. Ollama'nın native
tool API'sine bağlı değildir; farklı modellerle aynı kod çalışır.

Argümanlardaki komut metinleri `{}` içerebilir (örn. `find ... -exec rm {} \\;`).
Bu yüzden brace-balanced extractor kullanıyoruz — naive regex yetmez.
"""

from __future__ import annotations

import json
import re
from typing import Optional, TypedDict


class ToolCall(TypedDict):
    name: str
    arguments: dict


_TAG_OPEN = "<tool_call>"
_TAG_CLOSE = "</tool_call>"
_NAME_HINT = re.compile(r'"name"\s*:\s*"[^"]+"\s*,\s*"arguments"')


def extract_tool_call(content: str) -> Optional[ToolCall]:
    """LLM cevabından bir tool çağrısı varsa parse et, yoksa None.

    Strateji:
      1. <tool_call>...</tool_call> bloğu varsa içeriğini brace-balanced parse et
      2. Yoksa: content içinde `"name": "...", "arguments"` ipucunu bulup
         oradan geriye doğru `{`'a, ileri doğru balanced `}`'a kadar al
    """
    if not content:
        return None

    # 1) Tagged
    tag_start = content.find(_TAG_OPEN)
    if tag_start >= 0:
        body_start = tag_start + len(_TAG_OPEN)
        tag_end = content.find(_TAG_CLOSE, body_start)
        body = content[body_start:tag_end] if tag_end >= 0 else content[body_start:]
        candidate = _find_balanced_object(body)
        if candidate is not None:
            parsed = _safe_parse(candidate)
            if parsed:
                return parsed

    # 2) Fallback: ipucunu bul, etrafındaki balanced JSON'u çıkar
    match = _NAME_HINT.search(content)
    if match:
        # `{` ipucundan geriye doğru ara
        open_idx = content.rfind("{", 0, match.start())
        if open_idx >= 0:
            candidate = _extract_balanced(content, open_idx)
            if candidate is not None:
                parsed = _safe_parse(candidate)
                if parsed:
                    return parsed

    return None


def _find_balanced_object(text: str) -> Optional[str]:
    """text içindeki ilk balanced `{...}` bloğunu döner."""
    open_idx = text.find("{")
    if open_idx < 0:
        return None
    return _extract_balanced(text, open_idx)


def _extract_balanced(text: str, start: int) -> Optional[str]:
    """text[start] = '{' olmalı. Balanced kapanışa kadar substring döner.

    String literal'leri ("...") içindeki braces sayılmaz; backslash ile
    escape edilmiş tırnaklar atlanır.
    """
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _safe_parse(candidate: str) -> Optional[ToolCall]:
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if _is_valid_tool_call(data):
        return data  # type: ignore[return-value]
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
