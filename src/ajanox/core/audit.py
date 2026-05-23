"""Audit logging — her güvenlik aksiyonu JSON Lines olarak diske."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


AUDIT_DIR = Path(os.environ.get("AJANOX_HOME", str(Path.home() / ".ajanox")))
AUDIT_FILE = AUDIT_DIR / "audit.log"


def _ensure_dir() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log_event(event_type: str, **fields: Any) -> None:
    """Bir audit kaydı oluştur. Hatayı yutar — audit fail olursa app crash olmasın."""
    try:
        _ensure_dir()
        entry = {"ts": _now_iso(), "event": event_type, **fields}
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_tool_call(
    skill: str,
    tool: str,
    args: dict,
    approved: bool,
    approval_type: str = "auto",
) -> None:
    log_event(
        "tool_call",
        skill=skill,
        tool=tool,
        args=args,
        approved=approved,
        approval_type=approval_type,
    )


def log_approval_prompt(skill: str, tool: str, args: dict, user_response: str) -> None:
    log_event(
        "approval_prompt",
        skill=skill,
        tool=tool,
        args=args,
        user_response=user_response,
    )


def log_permission_denied(skill: str, reason: str) -> None:
    log_event("permission_denied", skill=skill, reason=reason)


def log_skill_load(skill: str, version: str, permissions: list[str]) -> None:
    log_event("skill_load", skill=skill, version=version, permissions=permissions)


def log_verification(verdict: str, warning_codes: list[str], mode: str) -> None:
    log_event(
        "verification",
        verdict=verdict,
        warning_codes=warning_codes,
        mode=mode,
    )
