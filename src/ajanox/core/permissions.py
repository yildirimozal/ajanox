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
    "file_read": RiskLevel.LOW,
    "file_write": RiskLevel.HIGH,
    "shell_safe": RiskLevel.LOW,
    "shell_unsafe": RiskLevel.HIGH,
    "network_read": RiskLevel.MEDIUM,
    "network_write": RiskLevel.HIGH,
    "process_read": RiskLevel.LOW,
    "process_control": RiskLevel.HIGH,
    "system_info": RiskLevel.LOW,
    "notification": RiskLevel.LOW,
    "audio_play": RiskLevel.LOW,
    "clipboard": RiskLevel.MEDIUM,
    "lib_execute": RiskLevel.MEDIUM,
    "sudo": RiskLevel.CRITICAL,
}


# v0.x boyunca yasak permission'lar (Spec kararı C — sudo v1.0'da gelecek).
FORBIDDEN_PERMISSIONS: frozenset[str] = frozenset({"sudo"})


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
