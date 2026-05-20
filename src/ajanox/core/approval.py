"""Runtime onay promptları + oturum cache.

Yüksek/kritik risk tool çağrılarında kullanıcıya görünür prompt.
"T (Tümü)" seçeneği aynı skill+tool kombinasyonu için oturum boyunca otomatik onay.

`sudo` permission seviyesinde T seçeneği YOK — her seferinde sorulur (Spec kararı).

Pluggable handler API:
    Web dashboard veya başka UI, `set_handler(callable)` ile terminal prompt'unu
    geçersiz kılabilir. Handler signature:

        handler(skill, tool, command_preview, risk, allow_session) -> str
            "yes" | "no" | "all"

    "all" sadece allow_session=True iken anlamlı — session cache'e eklenir.
"""

from __future__ import annotations

from typing import Callable, Optional


_SESSION_APPROVED: set[tuple[str, str]] = set()
_AUTO_APPROVE = False  # tests için
_HANDLER: Optional[Callable[[str, str, str, str, bool], str]] = None


def set_auto_approve(value: bool) -> None:
    """Tests için: tüm prompt'ları otomatik onayla."""
    global _AUTO_APPROVE
    _AUTO_APPROVE = value


def set_handler(handler: Optional[Callable[[str, str, str, str, bool], str]]) -> None:
    """Terminal prompt yerine kullanılacak callable. None → terminal'e geri dön."""
    global _HANDLER
    _HANDLER = handler


def reset_session() -> None:
    _SESSION_APPROVED.clear()


def _terminal_prompt(
    skill: str, tool: str, command_preview: str, risk: str, allow_session: bool
) -> str:
    preview = command_preview if len(command_preview) <= 100 else command_preview[:97] + "…"
    options = "[E]vet  [H]ayır" + ("  [T]ümünü bu oturum" if allow_session else "")

    print()
    print("┌─ Ajanox Güvenlik Onayı " + "─" * 36)
    print(f"│  Skill:    {skill}")
    print(f"│  İstenen:  {tool} ({risk} risk)")
    print(f"│  İçerik:   {preview}")
    print("│")
    print(f"│  İzin ver? {options}")
    print("└" + "─" * 60)

    try:
        response = input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "no"

    if allow_session and response in ("t", "tum", "tümü", "tumu"):
        return "all"
    if response in ("e", "evet", "y", "yes"):
        return "yes"
    return "no"


def request_approval(
    skill: str,
    tool: str,
    command_preview: str,
    risk: str = "high",
    allow_session: bool = True,
) -> bool:
    """Kullanıcıya onay sorgusu. True = onaylandı, False = reddedildi.

    Sıra: auto_approve → session cache → custom handler → terminal prompt.
    """
    if _AUTO_APPROVE:
        return True

    key = (skill, tool)
    if allow_session and key in _SESSION_APPROVED:
        return True

    prompt = _HANDLER if _HANDLER else _terminal_prompt
    try:
        decision = prompt(skill, tool, command_preview, risk, allow_session)
    except Exception:
        decision = "no"

    if decision == "all" and allow_session:
        _SESSION_APPROVED.add(key)
        return True
    if decision == "yes":
        return True
    return False
