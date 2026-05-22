"""Permission management.

Skill manifest'indeki permission'lar runtime kontrolünün veri tabanı.
Spec: docs/SPEC.md §3, docs/SECURITY.md
"""

from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# v0.1 permission seti. Spec'in §3 tablosuyla birebir uyumlu olmalı.
PERMISSION_RISK: dict[str, RiskLevel] = {
    # --- ENFORCED: enforcer.classify_tool_call bu kategorileri üretir ---
    "file_read": RiskLevel.LOW,
    "file_write": RiskLevel.HIGH,
    "shell_safe": RiskLevel.LOW,
    "shell_unsafe": RiskLevel.HIGH,
    "network_read": RiskLevel.MEDIUM,
    "network_write": RiskLevel.HIGH,
    "notification": RiskLevel.LOW,
    # --- RESERVED: manifest'te beyan edilebilir ama henüz hiçbir classifier/
    # primitive bu kategoriyi ÜRETMEZ. Yani tek başına beyan etmek bir yetki
    # VERMEZ (ör. process_control beyan eden bir skill yine de `kill` için
    # shell_unsafe'e ihtiyaç duyar). İlgili primitive/sınıflandırma gelene kadar
    # bunlar yalnızca deklaratiftir — bkz RESERVED_PERMISSIONS. ---
    "process_read": RiskLevel.LOW,
    "process_control": RiskLevel.HIGH,
    "system_info": RiskLevel.LOW,
    "audio_play": RiskLevel.LOW,
    "clipboard": RiskLevel.MEDIUM,
    "lib_execute": RiskLevel.MEDIUM,
    # --- FORBIDDEN ---
    "sudo": RiskLevel.CRITICAL,
}


# v0.x boyunca yasak permission'lar (Spec kararı C — sudo v1.0'da gelecek).
FORBIDDEN_PERMISSIONS: frozenset[str] = frozenset({"sudo"})


# Geçerli ama henüz uygulanmayan ("reserved") permission'lar. Bunları beyan etmek
# manifest doğrulamasından geçer fakat tek başına bir tool çağrısına izin vermez;
# enforcer hiçbir çağrıyı bu kategorilere sınıflandırmaz. False sense of security
# vermemek için ayrıca işaretlenir (skill check bunları "reserved" olarak gösterebilir).
RESERVED_PERMISSIONS: frozenset[str] = frozenset(
    {
        "process_read",
        "process_control",
        "system_info",
        "audio_play",
        "clipboard",
        "lib_execute",
    }
)


def get_risk(permission: str) -> RiskLevel | None:
    return PERMISSION_RISK.get(permission)


def is_runtime_approval_required(permission: str) -> bool:
    """High/critical risk → her seferinde runtime onayı."""
    risk = PERMISSION_RISK.get(permission)
    return risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)


def validate_permissions(
    declared: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """Manifest permission'larını doğrula.

    Returns: (valid, unknown, forbidden)
    """
    valid: list[str] = []
    unknown: list[str] = []
    forbidden: list[str] = []
    for p in declared:
        if p in FORBIDDEN_PERMISSIONS:
            forbidden.append(p)
        elif p in PERMISSION_RISK:
            valid.append(p)
        else:
            unknown.append(p)
    return valid, unknown, forbidden
