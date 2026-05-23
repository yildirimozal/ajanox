"""Skill ↔ Ajanox sürüm uyum kontrolü.

SPEC §1: "Marketplace skill'leri otomatik uyum kontrolünden geçer
(`ajanox` range uyumlu mu)." Bu modül o sözleşmeyi uygular.

Skill manifest'i `ajanox: ">=1.0.0 <2.0.0"` gibi bir semver aralığı belirtir.
Yüklü Ajanox sürümü bu aralığı sağlamıyorsa skill katalogdan çıkarılır.

Desteklenen operatörler: >=, >, <=, <, ==, ~=  (boşlukla ayrılmış AND'lenir).
Prerelease etiketleri (-alpha vb.) karşılaştırmada sayısal kısma indirgenir.
"""

from __future__ import annotations

import re
from typing import Callable


# MAJOR.MINOR.PATCH (+ opsiyonel -prerelease / +build, karşılaştırmada yok sayılır)
_VERSION_RE = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)")
_CLAUSE_RE = re.compile(r"(>=|<=|==|~=|>|<)\s*([0-9].*?)(?=\s|$)")

Version = tuple[int, int, int]


def parse_version(text: str) -> Version | None:
    """'1.2.3' → (1, 2, 3). Geçersizse None."""
    m = _VERSION_RE.match(text.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _cmp(a: Version, b: Version) -> int:
    return (a > b) - (a < b)


_OPS: dict[str, Callable[[int], bool]] = {
    ">=": lambda c: c >= 0,
    ">": lambda c: c > 0,
    "<=": lambda c: c <= 0,
    "<": lambda c: c < 0,
    "==": lambda c: c == 0,
}


def satisfies(version: str, constraint: str) -> bool:
    """version, constraint aralığını sağlıyor mu?

    Boş/eksik constraint → True (kısıt yok). Parse edilemeyen clause yok sayılır
    (güvenli taraf: skill'i körlemesine engelleme; ama tüm clause'lar parse
    edilemezse de True döner — deklaratif alan, sertçe reddetme).
    """
    v = parse_version(version)
    if v is None or not constraint or not constraint.strip():
        return True

    clauses = _CLAUSE_RE.findall(constraint)
    if not clauses:
        return True

    for op, ver_text in clauses:
        target = parse_version(ver_text)
        if target is None:
            continue  # parse edilemeyen clause'u atla
        if op == "~=":
            # ~=1.2.3 → >=1.2.3, <1.3.0 (compatible release)
            if _cmp(v, target) < 0:
                return False
            if not (v[0] == target[0] and v[1] == target[1]):
                return False
            continue
        check = _OPS.get(op)
        if check and not check(_cmp(v, target)):
            return False
    return True


def check_skill(ajanox_constraint: str, current: str) -> tuple[bool, str]:
    """Skill'in `ajanox` constraint'i geçerli sürümle uyumlu mu?

    Returns: (ok, reason). ok=False ise reason kullanıcıya gösterilir.
    """
    if satisfies(current, ajanox_constraint):
        return True, ""
    return False, f"Ajanox {current}, skill aralığı '{ajanox_constraint}' ile uyumsuz"
