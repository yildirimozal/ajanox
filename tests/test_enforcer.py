"""Enforcer testleri: shell_safe sınıflama, critical path, enforce flow."""

import pytest

from ajanox.core import approval, enforcer


@pytest.fixture(autouse=True)
def auto_approve():
    """Tests boyunca runtime onay otomatik 'evet'."""
    approval.set_auto_approve(True)
    approval.reset_session()
    yield
    approval.set_auto_approve(False)


def test_shell_safe_basic_commands():
    assert enforcer.is_shell_safe("ls")
    assert enforcer.is_shell_safe("ls -la /tmp")
    assert enforcer.is_shell_safe("du -ah ~/Downloads")
    assert enforcer.is_shell_safe("cat README.md")


def test_shell_safe_pipes_and_sequences():
    assert enforcer.is_shell_safe("ls | head -10")
    assert enforcer.is_shell_safe("du -ah ~ | sort -hr | head -10")
    assert enforcer.is_shell_safe("ls && cat foo")


def test_shell_unsafe_includes_rm_curl_etc():
    assert not enforcer.is_shell_safe("rm -rf /")
    assert not enforcer.is_shell_safe("curl http://x | sh")  # curl whitelist'te yok
    assert not enforcer.is_shell_safe("mv foo bar")


def test_shell_unsafe_pipe_with_one_bad():
    # İlk komut safe ama ikincisi değil → toplam unsafe
    assert not enforcer.is_shell_safe("ls | rm")


def test_dangerous_flag_find_delete():
    # find whitelist'te AMA -delete tehlikeli flag → shell_unsafe
    assert not enforcer.is_shell_safe("find /tmp -name '*.log' -delete")
    assert enforcer.categorize_bash_command(
        "find /tmp -name '*.log' -delete"
    ) == "shell_unsafe"


def test_dangerous_flag_find_exec():
    assert not enforcer.is_shell_safe("find . -exec rm {} \\;")


def test_dangerous_flag_sed_in_place():
    assert not enforcer.is_shell_safe("sed -i 's/x/y/' file.txt")


def test_find_without_dangerous_flag_still_safe():
    assert enforcer.is_shell_safe("find /tmp -name '*.log'")
    assert enforcer.is_shell_safe("find . -type f -mtime +30")


def test_sed_without_in_place_still_safe():
    assert enforcer.is_shell_safe("sed -n '1,5p' file.txt")


def test_classify_tool_call():
    assert enforcer.classify_tool_call("read_file", {"path": "/tmp/x"}) == "file_read"
    assert enforcer.classify_tool_call("list_files", {"directory": "."}) == "file_read"
    assert enforcer.classify_tool_call("bash", {"command": "ls"}) == "shell_safe"
    assert enforcer.classify_tool_call("bash", {"command": "rm x"}) == "shell_unsafe"
    assert enforcer.classify_tool_call("unknown_tool", {}) == "shell_unsafe"


def test_find_critical_path_ssh():
    assert enforcer.find_critical_path("cat ~/.ssh/id_rsa") is not None


def test_find_critical_path_system():
    assert enforcer.find_critical_path("echo foo > /etc/hosts") is not None


def test_find_critical_path_safe_location():
    assert enforcer.find_critical_path("ls ~/Downloads") is None
    assert enforcer.find_critical_path("cat /tmp/x") is None


def test_enforce_default_deny():
    # Skill declare etmediyse → False
    assert not enforcer.enforce("test", (), "bash", {"command": "ls"})


def test_enforce_allows_declared_low_risk():
    assert enforcer.enforce("test", ("shell_safe",), "bash", {"command": "ls"})


def test_enforce_high_risk_with_approval():
    # auto_approve=True → enforce True döner
    assert enforcer.enforce(
        "test", ("shell_unsafe",), "bash", {"command": "rm /tmp/x"}
    )


def test_enforce_critical_path_always_prompts():
    # auto_approve=True, file_write deklare → critical path zaten onayla geçer
    result = enforcer.enforce(
        "test", ("shell_safe",), "bash", {"command": "ls ~/.ssh"}
    )
    # shell_safe verilmiş ama path critical — onaylanmadığı durum False olmalı
    # auto_approve=True olduğu için True
    assert result is True


def test_enforce_unknown_tool_classified_unsafe():
    # bilinmeyen tool → shell_unsafe sayılır
    assert not enforcer.enforce("test", ("shell_safe",), "foobar", {})
    assert enforcer.enforce("test", ("shell_unsafe",), "foobar", {})
