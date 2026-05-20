"""Permission ve whitelist enforcement (Ajanox güvenlik middleware'i).

Skill bir tool çağrısı yaptığında, primitives'i çağırmadan önce bu modül:
  1. Çağrı türünü sınıflandırır (file_read, shell_safe, shell_unsafe, vs.)
  2. Skill'in declare ettiği permission setine bakar (default-deny)
  3. Düşük risk → sessiz devam
  4. Yüksek risk → runtime onay
  5. Critical path tespiti → her zaman onay
  6. Audit log her durumda

Spec: docs/SECURITY.md §3
"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import Iterable

import yaml


_TILDE_PATTERN = re.compile(r"(^|[\s'\"])~(?=/|$|\s)")


def _expand_tildes(text: str) -> str:
    """Komut metni içindeki ~/ ifadelerini home dir ile genişlet."""
    home = os.path.expanduser("~")
    return _TILDE_PATTERN.sub(lambda m: m.group(1) + home, text)

from . import approval, audit
from .permissions import (
    PERMISSION_RISK,
    RiskLevel,
    is_runtime_approval_required,
)


_WHITELIST_PATH = Path(__file__).parent / "whitelist.yml"
_CRITICAL_PATHS_PATH = Path(__file__).parent / "critical_paths.yml"


def _load_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}


_WHITELIST_DATA = _load_yaml(_WHITELIST_PATH)
_SHELL_SAFE_BINARIES: set[str] = set(_WHITELIST_DATA.get("shell_safe_commands", []))
_NETWORK_BINARIES: set[str] = set(_WHITELIST_DATA.get("network_binaries", []))
_NOTIFICATION_BINARIES: set[str] = set(_WHITELIST_DATA.get("notification_binaries", []))
_NETWORK_WRITE_INDICATORS: list[str] = list(
    _WHITELIST_DATA.get("network_write_indicators", [])
)

_CRITICAL_PATHS = [
    os.path.expanduser(p)
    for p in _load_yaml(_CRITICAL_PATHS_PATH).get("critical_paths", [])
]


def _split_segments(command: str) -> list[str]:
    """Komutu pipe / sequence operatörleri ile böl."""
    normalized = command
    for sep in ("&&", "||"):
        normalized = normalized.replace(sep, ";")
    normalized = normalized.replace("|", ";")
    return [s.strip() for s in normalized.split(";") if s.strip()]


def _first_binary(segment: str) -> str | None:
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return None
    if not tokens:
        return None
    return Path(tokens[0]).name


def _has_network_write_indicator(command: str) -> bool:
    return any(indicator in command for indicator in _NETWORK_WRITE_INDICATORS)


# Kategori risk sıralaması (artan): yüksek risk varsa o kazanır.
_CATEGORY_RANK = {
    "shell_safe": 0,
    "notification": 1,
    "network_read": 2,
    "network_write": 3,
    "shell_unsafe": 4,
}


def _categorize_segment(segment: str) -> str:
    """Tek bir komut segmentini kategoriye ata."""
    binary = _first_binary(segment)
    if binary is None:
        return "shell_unsafe"

    if binary in _NETWORK_BINARIES:
        return "network_write" if _has_network_write_indicator(segment) else "network_read"
    if binary in _NOTIFICATION_BINARIES:
        return "notification"
    if binary in _SHELL_SAFE_BINARIES:
        return "shell_safe"
    return "shell_unsafe"


def categorize_bash_command(command: str) -> str:
    """Bash komutunu permission kategorisine ata.

    Pipe segmentleri ayrı ayrı sınıflandırılır; en yüksek risk kategorisi döner.
    """
    if not command or not command.strip():
        return "shell_unsafe"
    segments = _split_segments(command)
    if not segments:
        return "shell_unsafe"
    return max(
        (_categorize_segment(s) for s in segments),
        key=lambda c: _CATEGORY_RANK.get(c, 99),
    )


def is_shell_safe(command: str) -> bool:
    """Geri uyumluluk: komut tamamı shell_safe kategorisindeyse True."""
    return categorize_bash_command(command) == "shell_safe"


def find_critical_path(command_or_path: str) -> str | None:
    """Komut veya yol critical path'e dokunuyorsa onu döner."""
    if not command_or_path:
        return None
    expanded = _expand_tildes(command_or_path)
    for path in _CRITICAL_PATHS:
        if path in expanded:
            return path
    return None


def classify_tool_call(tool: str, args: dict) -> str:
    """Bir tool çağrısının hangi permission'a denk düştüğünü söyle."""
    if tool == "read_file":
        return "file_read"
    if tool == "list_files":
        return "file_read"
    if tool == "bash":
        return categorize_bash_command(args.get("command", ""))
    return "shell_unsafe"  # bilinmeyen tool → en yüksek risk varsay


def enforce(
    skill_name: str,
    declared_permissions: Iterable[str],
    tool: str,
    args: dict,
    skill_location: str | None = None,
) -> bool:
    """Bu tool çağrısı yapılabilir mi?

    Args:
        skill_name: aktif skill adı (veya "system" ad-hoc için)
        declared_permissions: skill'in manifest'inde deklare ettiği permission seti
        tool: çağrılan tool adı (read_file, list_files, bash)
        args: tool argümanları
        skill_location: aktif skill'in SKILL.md yolu (self-introspection bypass için)

    Returns: True = devam, False = ret
    Yan etki: audit log + (gerekirse) kullanıcıya runtime onay
    """
    declared = set(declared_permissions)

    # Self-introspection: skill kendi SKILL.md dosyasını her zaman okuyabilir
    # (lazy-load mimarisinin doğal gereksinimi).
    if (
        tool == "read_file"
        and skill_location
        and args.get("path") == skill_location
    ):
        audit.log_tool_call(skill_name, tool, args, True, "self_introspection")
        return True

    required = classify_tool_call(tool, args)

    # 1) Default-deny: declare yoksa hayır
    if required not in declared:
        audit.log_permission_denied(
            skill_name,
            f"{required} needed but not declared "
            f"(declared: {sorted(declared) or '[]'})",
        )
        return False

    # 2) Critical path tespiti (bash veya file ops için)
    crit_target = None
    if tool == "bash":
        crit_target = find_critical_path(args.get("command", ""))
    elif tool in ("read_file", "list_files"):
        # Sadece write için critical kontrol mantıklı, read için skip
        pass

    if crit_target:
        ok = approval.request_approval(
            skill_name,
            tool,
            f"{args.get('command', '')} (CRITICAL PATH: {crit_target})",
            risk="critical",
            allow_session=False,
        )
        audit.log_approval_prompt(skill_name, tool, args, "yes" if ok else "no")
        if not ok:
            return False
        audit.log_tool_call(skill_name, tool, args, True, "user_critical")
        return True

    # 3) Yüksek/kritik risk → runtime onay
    if is_runtime_approval_required(required):
        cmd_preview = args.get("command", str(args))
        ok = approval.request_approval(
            skill_name, tool, cmd_preview, risk=required
        )
        audit.log_approval_prompt(skill_name, tool, args, "yes" if ok else "no")
        if not ok:
            return False
        audit.log_tool_call(skill_name, tool, args, True, "user_runtime")
        return True

    # 4) Düşük/orta risk: sessiz devam
    audit.log_tool_call(skill_name, tool, args, True, "auto")
    return True
