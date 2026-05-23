"""Audit logger testleri."""

import json

import pytest


@pytest.fixture
def isolated_audit(tmp_path, monkeypatch):
    """Tests için audit dosyasını izole tmp_path'e yönlendir."""
    monkeypatch.setenv("AJANOX_HOME", str(tmp_path))
    # audit modülünün modül-seviyesi sabitlerini reload et
    import importlib
    from ajanox.core import audit as audit_mod
    importlib.reload(audit_mod)
    yield audit_mod, tmp_path / "audit.log"
    importlib.reload(audit_mod)  # state reset


def test_log_event_creates_file_and_appends(isolated_audit):
    audit, log_path = isolated_audit
    audit.log_event("test_event", foo="bar")
    audit.log_event("test_event", foo="baz")

    assert log_path.exists()
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    entry = json.loads(lines[0])
    assert entry["event"] == "test_event"
    assert entry["foo"] == "bar"
    assert "ts" in entry


def test_log_tool_call_structure(isolated_audit):
    audit, log_path = isolated_audit
    audit.log_tool_call("weather", "bash", {"command": "curl"}, True, "auto")
    entry = json.loads(log_path.read_text().strip())
    assert entry["event"] == "tool_call"
    assert entry["skill"] == "weather"
    assert entry["approved"] is True
    assert entry["approval_type"] == "auto"


def test_log_permission_denied(isolated_audit):
    audit, log_path = isolated_audit
    audit.log_permission_denied("bad-skill", "shell_unsafe not declared")
    entry = json.loads(log_path.read_text().strip())
    assert entry["event"] == "permission_denied"
    assert entry["reason"] == "shell_unsafe not declared"


def test_unicode_safe(isolated_audit):
    audit, log_path = isolated_audit
    audit.log_event("test", komut="rm -rf ~/Çöp")
    entry = json.loads(log_path.read_text().strip())
    assert "Çöp" in entry["komut"]
