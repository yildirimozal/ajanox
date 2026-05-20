"""Runtime onay promptları + oturum cache.

Yüksek/kritik risk tool çağrılarında kullanıcıya görünür prompt.
"T (Tümü)" seçeneği aynı skill+tool kombinasyonu için oturum boyunca otomatik onay.

`sudo` permission seviyesinde T seçeneği YOK — her seferinde sorulur (Spec kararı).
"""

from __future__ import annotations


_SESSION_APPROVED: set[tuple[str, str]] = set()
_AUTO_APPROVE = False  # tests için


def set_auto_approve(value: bool) -> None:
    """Tests için: tüm prompt'ları otomatik onayla."""
    global _AUTO_APPROVE
    _AUTO_APPROVE = value


def reset_session() -> None:
    _SESSION_APPROVED.clear()


def request_approval(
    skill: str,
    tool: str,
    command_preview: str,
    risk: str = "high",
    allow_session: bool = True,
) -> bool:
    """Kullanıcıya onay sorgusu. True = onaylandı, False = reddedildi.

    Args:
        skill: skill adı
        tool: tool adı (read_file, bash, vs.)
        command_preview: komut özeti (bash için komut metni, dosya için yol)
        risk: "high" veya "critical"
        allow_session: "T (Tümü)" seçeneği gösterilsin mi (sudo'da False)
    """
    if _AUTO_APPROVE:
        return True

    key = (skill, tool)
    if allow_session and key in _SESSION_APPROVED:
        return True

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
        return False

    if allow_session and response in ("t", "tum", "tümü", "tumu"):
        _SESSION_APPROVED.add(key)
        return True
    if response in ("e", "evet", "y", "yes"):
        return True
    return False
