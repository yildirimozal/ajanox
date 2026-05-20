"""Permission tablosu + validation testleri."""

from ajanox.core.permissions import (
    FORBIDDEN_PERMISSIONS,
    PERMISSION_RISK,
    RiskLevel,
    is_runtime_approval_required,
    validate_permissions,
)


def test_known_permissions_have_risk_levels():
    # Spec v0.1'in 14 permission'ı tabloda olmalı
    expected = {
        "file_read", "file_write", "shell_safe", "shell_unsafe",
        "network_read", "network_write", "process_read", "process_control",
        "system_info", "notification", "audio_play", "clipboard",
        "lib_execute", "sudo",
    }
    assert set(PERMISSION_RISK.keys()) == expected


def test_sudo_is_critical():
    assert PERMISSION_RISK["sudo"] == RiskLevel.CRITICAL


def test_high_risk_requires_runtime_approval():
    assert is_runtime_approval_required("file_write")
    assert is_runtime_approval_required("shell_unsafe")
    assert is_runtime_approval_required("sudo")


def test_low_risk_no_runtime_approval():
    assert not is_runtime_approval_required("shell_safe")
    assert not is_runtime_approval_required("file_read")
    assert not is_runtime_approval_required("notification")


def test_validate_separates_valid_unknown_forbidden():
    valid, unknown, forbidden = validate_permissions(
        ["shell_safe", "file_read", "sudo", "fake_perm", "shell_unsafe"]
    )
    assert set(valid) == {"shell_safe", "file_read", "shell_unsafe"}
    assert unknown == ["fake_perm"]
    assert forbidden == ["sudo"]


def test_forbidden_includes_sudo():
    assert "sudo" in FORBIDDEN_PERMISSIONS
