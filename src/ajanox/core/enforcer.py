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

import fnmatch
import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

from . import approval, audit
from .permissions import is_runtime_approval_required


_TILDE_PATTERN = re.compile(r"(^|[\s'\"])~(?=/|$|\s)")


def _expand_tildes(text: str) -> str:
    """Komut metni içindeki ~/ ve $HOME ifadelerini home dir ile genişlet."""
    home = os.path.expanduser("~")
    text = _TILDE_PATTERN.sub(lambda m: m.group(1) + home, text)
    return text.replace("${HOME}", home).replace("$HOME", home)


_WHITELIST_PATH = Path(__file__).parent / "whitelist.yml"
_CRITICAL_PATHS_PATH = Path(__file__).parent / "critical_paths.yml"
_SENSITIVE_READ_PATH = Path(__file__).parent / "sensitive_read.yml"


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
_DANGEROUS_FLAGS: dict[str, list[str]] = dict(
    _WHITELIST_DATA.get("dangerous_flags", {})
)

_CRITICAL_PATHS = [
    os.path.expanduser(p)
    for p in _load_yaml(_CRITICAL_PATHS_PATH).get("critical_paths", [])
]

_SENSITIVE_DATA = _load_yaml(_SENSITIVE_READ_PATH)
_SENSITIVE_READ_PATHS = [
    os.path.expanduser(p) for p in _SENSITIVE_DATA.get("sensitive_read_paths", [])
]
_SENSITIVE_READ_GLOBS: list[str] = list(_SENSITIVE_DATA.get("sensitive_read_globs", []))


def _split_segments(command: str) -> list[str]:
    """Komutu pipe / sequence / newline operatörleriyle böl (tırnak-duyarlı).

    Tırnak içindeki | && || ; ve newline operatör SAYILMAZ — böylece
    `grep "a|b" f` gibi komutlar yanlışlıkla parçalanıp shell_unsafe olmaz.
    Tek & (background) burada bölünmez; _scan_shell_features onu yakalar.
    """
    segments: list[str] = []
    buf: list[str] = []
    n = len(command)
    i = 0
    quote: str | None = None
    while i < n:
        c = command[i]
        if quote:
            buf.append(c)
            if c == "\\" and quote == '"' and i + 1 < n:
                buf.append(command[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"":
            quote = c
            buf.append(c)
            i += 1
            continue
        if c in "\n\r;":
            segments.append("".join(buf))
            buf = []
            i += 1
            continue
        if c == "|":  # | veya ||
            segments.append("".join(buf))
            buf = []
            i += 2 if (i + 1 < n and command[i + 1] == "|") else 1
            continue
        if c == "&" and i + 1 < n and command[i + 1] == "&":  # &&
            segments.append("".join(buf))
            buf = []
            i += 2
            continue
        buf.append(c)
        i += 1
    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]


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
    "file_write": 3,
    "network_write": 4,
    "shell_unsafe": 5,
}


# Yazma sayılmayan benign redirect hedefleri (>/dev/null gibi yaygın, zararsız).
_BENIGN_REDIRECT_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty"}


@dataclass
class _ShellFeatures:
    """_split_segments operatörlerinin görmediği kabuk metakarakterleri."""

    write_targets: list[str] = field(default_factory=list)  # >, >>, >|, &>, N>
    subst_commands: list[str] = field(default_factory=list)  # $(...) ve `...` içi
    has_proc_subst: bool = False  # <( ) veya >( )
    has_background: bool = False  # tek & (&& değil)
    has_unparsed_subst: bool = False  # $( / ` görüldü ama balanced çıkmadı


def _extract_balanced_parens(text: str, start: int) -> tuple[str | None, int]:
    """text[start] == '(' olmalı. İç içeriği + kapanış sonrası index'i döner.

    String literal'leri içindeki parantezler sayılmaz. Bulunamazsa (None, start).
    """
    if start >= len(text) or text[start] != "(":
        return None, start
    depth = 0
    j = start
    tq: str | None = None
    while j < len(text):
        ch = text[j]
        if tq:
            if ch == "\\" and tq == '"':
                j += 2
                continue
            if ch == tq:
                tq = None
            j += 1
            continue
        if ch in "'\"":
            tq = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1 : j], j + 1
        j += 1
    return None, start


def _read_redirect_target(command: str, start: int) -> tuple[str, int]:
    """start'tan boşlukları atlayıp bir redirect hedef token'ı oku. (token, index)."""
    n = len(command)
    j = start
    while j < n and command[j] in " \t":
        j += 1
    tok_start = j
    tq: str | None = None
    while j < n:
        c = command[j]
        if tq:
            if c == tq:
                tq = None
            j += 1
            continue
        if c in "'\"":
            tq = c
            j += 1
            continue
        if c in " \t\n;|&<>()":
            break
        j += 1
    return command[tok_start:j].replace("'", "").replace('"', ""), j


def _scan_shell_features(command: str) -> _ShellFeatures:
    """Komutu tırnak-duyarlı tara: redirect, command/process substitution, background.

    `shell=True` ile çalışan komutlar için, sınıflandırmanın kör noktası olan
    metakarakterleri yakalar. Tek tırnak her şeyi literal yapar; çift tırnak
    içinde command substitution ($(...), `...`) hâlâ aktiftir.
    """
    feats = _ShellFeatures()
    n = len(command)
    i = 0
    quote: str | None = None  # "'" | '"' | None

    while i < n:
        c = command[i]

        # Tek tırnak: tamamen literal
        if quote == "'":
            if c == "'":
                quote = None
            i += 1
            continue

        # Backslash escape (çift tırnak içi veya tırnak dışı)
        if c == "\\":
            i += 2
            continue

        # Tırnak aç/kapa
        if c == "'" and quote is None:
            quote = "'"
            i += 1
            continue
        if c == '"':
            quote = None if quote == '"' else '"'
            i += 1
            continue

        # Command substitution — çift tırnak içinde de aktif
        if c == "`":
            end = command.find("`", i + 1)
            if end < 0:
                feats.has_unparsed_subst = True
                break
            feats.subst_commands.append(command[i + 1 : end])
            i = end + 1
            continue
        if c == "$" and i + 1 < n and command[i + 1] == "(":
            inner, end = _extract_balanced_parens(command, i + 1)
            if inner is None:
                feats.has_unparsed_subst = True
                break
            feats.subst_commands.append(inner)
            i = end
            continue

        # Aşağıdakiler yalnızca tırnak DIŞINDA anlamlı
        if quote is not None:
            i += 1
            continue

        # process substitution <( ) / >( )
        if c in "<>" and i + 1 < n and command[i + 1] == "(":
            feats.has_proc_subst = True
            i += 2
            continue

        if c == "&":
            if i + 1 < n and command[i + 1] == "&":
                i += 2  # && logical — zararsız
                continue
            if i + 1 < n and command[i + 1] == ">":  # &> / &>>
                k = i + 2
                if k < n and command[k] == ">":
                    k += 1
                target, i = _read_redirect_target(command, k)
                feats.write_targets.append(target or "?")
                continue
            feats.has_background = True
            i += 1
            continue

        if c == ">":
            k = i + 1
            if k < n and command[k] in ">|":
                k += 1
            j = k
            while j < n and command[j] in " \t":
                j += 1
            if j < n and command[j] == "&":  # >&N fd duplication — dosya değil
                i = j + 1
                continue
            target, i = _read_redirect_target(command, k)
            feats.write_targets.append(target or "?")
            continue

        if c == "<":
            if i + 1 < n and command[i + 1] == "<":  # << heredoc — dosya değil
                i += 2
                continue
            i += 1  # girdi redirect — hassas hedef enforce()'ta tüm komutta taranır
            continue

        i += 1

    return feats


def _has_dangerous_flag(binary: str, segment: str) -> bool:
    """Binary için tehlikeli flag (örn. find -delete, sed -i) var mı?"""
    flags = _DANGEROUS_FLAGS.get(binary, [])
    if not flags:
        return False
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return True  # parse edemezsek güvensiz say
    return any(flag in tokens for flag in flags)


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
        # find -delete, sed -i gibi tehlikeli flag varsa shell_unsafe'e yükselt
        if _has_dangerous_flag(binary, segment):
            return "shell_unsafe"
        return "shell_safe"
    return "shell_unsafe"


def categorize_bash_command(command: str) -> str:
    """Bash komutunu permission kategorisine ata.

    Segmentler (pipe/sequence/newline) ayrı ayrı sınıflandırılır; ek olarak
    redirect, command/process substitution ve background gibi metakarakterler
    taranır. En yüksek risk kategorisi döner. İlke: sınıflandırıcının tam
    hesaplayamadığı her şeyde fail-closed (shell_unsafe).
    """
    if not command or not command.strip():
        return "shell_unsafe"

    segments = _split_segments(command)
    if not segments:
        return "shell_unsafe"

    categories: list[str] = [_categorize_segment(s) for s in segments]

    feats = _scan_shell_features(command)

    # Modellenemeyen özellikler → fail-closed
    if feats.has_proc_subst or feats.has_background or feats.has_unparsed_subst:
        categories.append("shell_unsafe")

    # Dosyaya redirect → file_write (/dev/null gibi benign hedefler hariç)
    if any(t.strip() not in _BENIGN_REDIRECT_TARGETS for t in feats.write_targets):
        categories.append("file_write")

    # Command substitution → iç komutlara özyinele, kategorilerini birleştir
    for inner in feats.subst_commands:
        if inner.strip():
            categories.append(categorize_bash_command(inner))

    return max(categories, key=lambda c: _CATEGORY_RANK.get(c, 99))


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


def _candidate_tokens(text: str) -> list[str]:
    """Bir komut/path'ten aday path token'ları çıkar."""
    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = text.split()
    # Boşluklu tek path (örn. ".../Login Data") için tüm metni de aday say.
    tokens.append(text)
    return tokens


def find_sensitive_read(command_or_path: str) -> str | None:
    """Komut veya yol OKUMA-hassas bir hedefe (kimlik/sır) dokunuyorsa onu döner.

    file_read LOW risk olsa bile bu eşleşmeler runtime onay tetikler — sessiz
    veri sızdırmayı kapatır. Eşleşme: hassas yol parçası, kimlik/sır dosya adı
    glob'u, veya $HOME altındaki herhangi bir dotfile.
    """
    if not command_or_path:
        return None
    expanded = _expand_tildes(command_or_path)

    for frag in _SENSITIVE_READ_PATHS:
        if frag in expanded:
            return frag

    home = os.path.expanduser("~")
    for tok in _candidate_tokens(expanded):
        base = os.path.basename(tok.rstrip("/"))
        if not base:
            continue
        for pat in _SENSITIVE_READ_GLOBS:
            if fnmatch.fnmatch(base, pat):
                return tok
        # $HOME altındaki dotfile'lar (.env, .netrc, .bash_history, ...)
        if base.startswith(".") and base not in (".", "..") and tok.startswith(home):
            return tok

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

    # Legacy mode: skill manifest'te hiç permission belirtmemişse
    # (eski format SKILL.md'ler), her tool çağrısı için runtime onay zorla.
    # Bu marketplace'ten yüklenen v0.x öncesi skill'lerin çalışabilmesi için.
    if not declared:
        cmd_preview = args.get("command", str(args))
        ok = approval.request_approval(
            skill_name, tool, cmd_preview, risk="legacy", allow_session=True
        )
        audit.log_approval_prompt(skill_name, tool, args, "yes" if ok else "no")
        if not ok:
            audit.log_permission_denied(
                skill_name, "legacy skill — user denied at runtime"
            )
            return False
        audit.log_tool_call(skill_name, tool, args, True, "user_legacy")
        return True

    # 1) Default-deny: declare yoksa hayır
    if required not in declared:
        audit.log_permission_denied(
            skill_name,
            f"{required} needed but not declared "
            f"(declared: {sorted(declared) or '[]'})",
        )
        return False

    # 2) Critical path (yazma-hassas) + sensitive read (kimlik/sır) tespiti.
    # Hem bash hem de read_file/list_files için: yazma-kritik yollar VE okuma-
    # hassas dosyalar her seferinde runtime onay gerektirir (file_read LOW olsa bile).
    if tool == "bash":
        scan = args.get("command", "")
    else:  # read_file / list_files
        scan = str(args.get("path") or args.get("directory") or "")

    crit_target = find_critical_path(scan) or find_sensitive_read(scan)

    if crit_target:
        preview = args.get("command") or scan or str(args)
        ok = approval.request_approval(
            skill_name,
            tool,
            f"{preview} (HASSAS: {crit_target})",
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
