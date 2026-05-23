"""Platform tespiti testleri."""

from __future__ import annotations

import pytest

from ajanox.core import platform as plat


@pytest.fixture(autouse=True)
def _clear_caches():
    """Her test öncesi lru_cache'leri temizle (monkeypatch izole olsun)."""
    plat.is_wsl.cache_clear()
    plat.current_os.cache_clear()
    yield
    plat.is_wsl.cache_clear()
    plat.current_os.cache_clear()


def _set_system(monkeypatch, value: str):
    monkeypatch.setattr(plat._platform, "system", lambda: value)


# --- current_os ---

def test_macos_detected(monkeypatch):
    _set_system(monkeypatch, "Darwin")
    assert plat.current_os() == "macos"


def test_linux_detected(monkeypatch):
    _set_system(monkeypatch, "Linux")
    monkeypatch.setattr(plat, "is_wsl", lambda: False)
    plat.current_os.cache_clear()
    assert plat.current_os() == "linux"


def test_windows_detected(monkeypatch):
    _set_system(monkeypatch, "Windows")
    assert plat.current_os() == "windows"


def test_wsl_detected_via_proc_version(monkeypatch, tmp_path):
    _set_system(monkeypatch, "Linux")
    proc = tmp_path / "version"
    proc.write_text("Linux version 5.15.0-microsoft-standard-WSL2")
    monkeypatch.setattr(plat, "Path", lambda p: proc if p == "/proc/version" else __import__("pathlib").Path(p))
    plat.is_wsl.cache_clear()
    plat.current_os.cache_clear()
    assert plat.is_wsl() is True
    assert plat.current_os() == "wsl"


def test_plain_linux_not_wsl(monkeypatch, tmp_path):
    _set_system(monkeypatch, "Linux")
    proc = tmp_path / "version"
    proc.write_text("Linux version 6.1.0-generic")
    monkeypatch.setattr(plat, "Path", lambda p: proc if p == "/proc/version" else __import__("pathlib").Path(p))
    plat.is_wsl.cache_clear()
    assert plat.is_wsl() is False


# --- os_aliases ---

def test_wsl_aliases_include_linux(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "wsl")
    assert plat.os_aliases() == frozenset({"wsl", "linux"})


def test_macos_aliases_include_darwin(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "macos")
    assert plat.os_aliases() == frozenset({"macos", "darwin"})


def test_linux_aliases_only_linux(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "linux")
    assert plat.os_aliases() == frozenset({"linux"})


# --- supports_skill_os ---

def test_no_constraint_supports_all(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "linux")
    assert plat.supports_skill_os(None) is True
    assert plat.supports_skill_os([]) is True


def test_matching_os_supported(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "macos")
    assert plat.supports_skill_os(["darwin"]) is True
    assert plat.supports_skill_os(["linux", "darwin"]) is True


def test_nonmatching_os_unsupported(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "macos")
    assert plat.supports_skill_os(["linux"]) is False
    assert plat.supports_skill_os(["windows"]) is False


def test_wsl_runs_linux_skills(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "wsl")
    assert plat.supports_skill_os(["linux"]) is True
    assert plat.supports_skill_os(["wsl"]) is True


def test_case_insensitive(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "linux")
    assert plat.supports_skill_os(["LINUX"]) is True


# --- hints ---

def test_ollama_hint_only_on_wsl(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "wsl")
    assert "WSL2" in plat.ollama_host_hint()
    monkeypatch.setattr(plat, "current_os", lambda: "linux")
    assert plat.ollama_host_hint() == ""


def test_describe_returns_label(monkeypatch):
    monkeypatch.setattr(plat, "current_os", lambda: "wsl")
    assert "WSL2" in plat.describe()
