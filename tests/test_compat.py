"""Sürüm uyum (compat) testleri."""

from __future__ import annotations

import pytest

from ajanox.core import compat


# --- parse_version ---

def test_parse_basic():
    assert compat.parse_version("1.2.3") == (1, 2, 3)


def test_parse_with_prerelease():
    assert compat.parse_version("1.0.0-alpha.1") == (1, 0, 0)


def test_parse_invalid():
    assert compat.parse_version("not-a-version") is None
    assert compat.parse_version("1.2") is None


# --- satisfies ---

@pytest.mark.parametrize("version,constraint,expected", [
    ("1.0.0", ">=1.0.0 <2.0.0", True),
    ("1.5.3", ">=1.0.0 <2.0.0", True),
    ("2.0.0", ">=1.0.0 <2.0.0", False),
    ("0.9.0", ">=1.0.0 <2.0.0", False),
    ("0.9.0", ">=0.2.0 <1.0.0", True),
    ("1.0.0", ">=0.2.0 <1.0.0", False),   # v1.0 temiz kesme
    ("1.0.0", ">=1.0", True),
    ("1.3.0", "==1.3.0", True),
    ("1.3.1", "==1.3.0", False),
    ("1.2.5", "~=1.2.0", True),           # compatible release
    ("1.3.0", "~=1.2.0", False),
    ("1.1.0", "~=1.2.0", False),
])
def test_satisfies(version, constraint, expected):
    assert compat.satisfies(version, constraint) is expected


def test_empty_constraint_always_satisfied():
    assert compat.satisfies("1.0.0", "") is True
    assert compat.satisfies("1.0.0", "   ") is True


def test_unparseable_version_permissive():
    # Sürüm parse edilemezse körlemesine engelleme
    assert compat.satisfies("garbage", ">=1.0.0") is True


def test_unparseable_clause_skipped():
    # Bir clause parse edilemese de diğerleri uygulanır
    assert compat.satisfies("1.5.0", ">=1.0.0 <garbage") is True
    assert compat.satisfies("0.9.0", ">=1.0.0 <garbage") is False


# --- check_skill ---

def test_check_skill_compatible():
    ok, reason = compat.check_skill(">=1.0.0 <2.0.0", "1.0.0")
    assert ok is True
    assert reason == ""


def test_check_skill_incompatible_reports_reason():
    ok, reason = compat.check_skill(">=0.2.0 <1.0.0", "1.0.0")
    assert ok is False
    assert "1.0.0" in reason and "1.0.0" in reason


def test_check_skill_no_constraint():
    ok, _ = compat.check_skill("", "1.0.0")
    assert ok is True
