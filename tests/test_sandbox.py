"""Sandbox modülü testleri.

Pure unit testler — bwrap/sandbox-exec'i gerçekten çalıştırmaz, sadece
argv/profile üretimini doğrular. Gerçek integration testleri ayrı
(`tests/test_sandbox_integration.py`, opsiyonel).
"""

from __future__ import annotations

import os

import pytest

from ajanox.core import sandbox


# --- mode handling ---

def test_get_mode_default(monkeypatch):
    monkeypatch.delenv("AJANOX_SANDBOX", raising=False)
    assert sandbox.get_mode() == "auto"


def test_get_mode_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("AJANOX_SANDBOX", "xyz")
    assert sandbox.get_mode() == "auto"


@pytest.mark.parametrize("value", ["auto", "on", "off"])
def test_get_mode_valid(monkeypatch, value):
    monkeypatch.setenv("AJANOX_SANDBOX", value)
    assert sandbox.get_mode() == value


# --- bwrap argv ---

def test_bwrap_default_unshares_net():
    argv = sandbox.build_bwrap_argv("ls", permissions=set())
    assert argv[0] == "bwrap"
    assert "--unshare-net" in argv
    assert "--share-net" not in argv


def test_bwrap_network_read_shares_net():
    argv = sandbox.build_bwrap_argv("curl https://x", permissions={"network_read"})
    assert "--share-net" in argv
    assert "--unshare-net" not in argv


def test_bwrap_network_write_shares_net():
    argv = sandbox.build_bwrap_argv("curl -X POST", permissions={"network_write"})
    assert "--share-net" in argv


def test_bwrap_masks_sensitive_home_dirs(monkeypatch):
    # Sensitive dirs sadece varsa maskelenir — testte var gibi davran
    monkeypatch.setattr(os.path, "exists", lambda p: p.endswith((".ssh", ".aws", ".gnupg")))
    monkeypatch.setattr(os.path, "isdir", lambda p: True)
    argv = sandbox.build_bwrap_argv("ls", permissions=set())
    home = os.path.expanduser("~")
    assert f"{home}/.ssh" in argv
    assert f"{home}/.aws" in argv
    # tmpfs ile maskelendiklerini doğrula
    for sensitive in (".ssh", ".aws", ".gnupg"):
        idx = argv.index(f"{home}/{sensitive}")
        assert argv[idx - 1] == "--tmpfs"


def test_bwrap_skips_nonexistent_sensitive_paths(monkeypatch):
    # Mevcut olmayan path'ler argv'ye eklenmez (bwrap --tmpfs ro-fs altında
    # var olmayan dest'e mount edemez)
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    argv = sandbox.build_bwrap_argv("ls", permissions=set())
    home = os.path.expanduser("~")
    assert f"{home}/.ssh" not in argv
    assert f"{home}/.aws" not in argv


def test_bwrap_masks_file_with_dev_null(monkeypatch):
    # .netrc gibi dosya hedefler --ro-bind /dev/null ile maskelenir
    monkeypatch.setattr(os.path, "exists", lambda p: p.endswith(".netrc"))
    monkeypatch.setattr(os.path, "isdir", lambda p: False)
    argv = sandbox.build_bwrap_argv("ls", permissions=set())
    home = os.path.expanduser("~")
    target = f"{home}/.netrc"
    assert target in argv
    idx = argv.index(target)
    assert argv[idx - 2 : idx] == ["--ro-bind", "/dev/null"]


def test_bwrap_command_appended_at_end():
    argv = sandbox.build_bwrap_argv("echo hi", permissions=set())
    # Son üç eleman: bash -c <command>
    assert argv[-3:] == ["bash", "-c", "echo hi"]
    # Komuttan hemen önce "--" separator
    assert argv[-4] == "--"


def test_bwrap_command_with_special_chars_not_split():
    cmd = "find /tmp -name '*.log' -exec rm {} \\;"
    argv = sandbox.build_bwrap_argv(cmd, permissions=set())
    assert argv[-1] == cmd  # tek string, shell-parsing yok


# --- sandbox-exec profile ---

def test_sandbox_exec_profile_denies_network_by_default():
    profile = sandbox.build_sandbox_exec_profile(permissions=set())
    assert "(deny network*)" in profile


def test_sandbox_exec_profile_allows_network_with_perm():
    profile = sandbox.build_sandbox_exec_profile(permissions={"network_read"})
    assert "(allow network*)" in profile


def test_sandbox_exec_profile_denies_sensitive_paths():
    profile = sandbox.build_sandbox_exec_profile(permissions=set())
    home = os.path.expanduser("~")
    assert f'(deny file-read* (subpath "{home}/.ssh"))' in profile
    assert f'(deny file-read* (subpath "{home}/.aws"))' in profile


def test_sandbox_exec_profile_file_write_widens_perms():
    base = sandbox.build_sandbox_exec_profile(permissions=set())
    widened = sandbox.build_sandbox_exec_profile(permissions={"file_write"})
    home = os.path.expanduser("~")
    assert f'{home}/Documents' not in base
    assert f'{home}/Documents' in widened


def test_sandbox_exec_profile_always_allows_tmp_write():
    profile = sandbox.build_sandbox_exec_profile(permissions=set())
    assert '/tmp' in profile
    assert 'file-write*' in profile


# --- plan() ---

def test_plan_off_returns_none_backend(monkeypatch):
    monkeypatch.setenv("AJANOX_SANDBOX", "off")
    p = sandbox.plan("echo hi", permissions=set())
    assert p.backend == "none"
    assert not p.blocked


def test_plan_on_without_backend_is_blocked(monkeypatch):
    monkeypatch.setenv("AJANOX_SANDBOX", "on")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "none")
    p = sandbox.plan("echo hi", permissions=set())
    assert p.blocked is True
    assert "backend yok" in (p.warning or "")


def test_plan_auto_without_backend_warns_no_block(monkeypatch):
    monkeypatch.setenv("AJANOX_SANDBOX", "auto")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "none")
    p = sandbox.plan("echo hi", permissions=set())
    assert p.blocked is False
    assert p.backend == "none"
    assert p.warning  # uyarı var


def test_plan_auto_with_bwrap_uses_bwrap(monkeypatch):
    monkeypatch.setenv("AJANOX_SANDBOX", "auto")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "bwrap")
    p = sandbox.plan("ls", permissions=set())
    assert p.backend == "bwrap"
    assert p.wrapped_argv[0] == "bwrap"
    assert p.wrapped_argv[-3:] == ["bash", "-c", "ls"]


def test_plan_auto_with_sandbox_exec_uses_sbx(monkeypatch):
    monkeypatch.setenv("AJANOX_SANDBOX", "auto")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "sandbox-exec")
    p = sandbox.plan("ls", permissions=set())
    assert p.backend == "sandbox-exec"
    assert p.wrapped_argv[0] == "sandbox-exec"
    assert p.profile_text is not None


# --- materialize() ---

def test_materialize_bwrap_passthrough(monkeypatch):
    monkeypatch.setenv("AJANOX_SANDBOX", "auto")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "bwrap")
    p = sandbox.plan("ls", permissions=set())
    argv, tmp = sandbox.materialize(p)
    assert argv == p.wrapped_argv
    assert tmp is None


def test_materialize_sandbox_exec_writes_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("AJANOX_SANDBOX", "auto")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "sandbox-exec")
    p = sandbox.plan("ls", permissions={"network_read"})
    argv, tmp = sandbox.materialize(p)
    assert tmp is not None
    assert os.path.exists(tmp)
    content = open(tmp).read()
    assert "(allow network*)" in content
    assert "<PROFILE_PATH>" not in argv
    assert tmp in argv
    os.unlink(tmp)


# --- primitives.bash sandbox wiring (mock subprocess) ---

def test_bash_uses_sandbox_argv_when_backend_available(monkeypatch):
    """bash() sandbox aktifken subprocess'e wrapped argv ile çağırmalı."""
    from ajanox.core import primitives

    monkeypatch.setenv("AJANOX_SANDBOX", "auto")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "bwrap")
    token = primitives.ACTIVE_PERMISSIONS.set(frozenset({"shell_unsafe"}))

    captured: dict = {}

    class _FakeResult:
        stdout = "ok\n"
        stderr = ""
        returncode = 0

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return _FakeResult()

    monkeypatch.setattr(primitives.subprocess, "run", fake_run)
    try:
        out = primitives.bash("echo hi")
    finally:
        primitives.ACTIVE_PERMISSIONS.reset(token)

    assert out == "ok"
    # Wrapped argv kullanılmış (shell=True YOK)
    assert captured["argv"][0] == "bwrap"
    assert captured["argv"][-3:] == ["bash", "-c", "echo hi"]
    assert captured["kwargs"].get("shell") is not True


def test_bash_falls_back_to_shell_when_no_backend(monkeypatch):
    """Sandbox backend yoksa eski shell=True yoluyla çalışmalı."""
    from ajanox.core import primitives

    monkeypatch.setenv("AJANOX_SANDBOX", "auto")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "none")

    captured: dict = {}

    class _FakeResult:
        stdout = "ok"
        stderr = ""
        returncode = 0

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return _FakeResult()

    monkeypatch.setattr(primitives.subprocess, "run", fake_run)
    out = primitives.bash("echo hi")
    assert out == "ok"
    assert captured["cmd"] == "echo hi"
    assert captured["kwargs"].get("shell") is True


def test_bash_blocked_when_sandbox_on_but_unavailable(monkeypatch):
    """AJANOX_SANDBOX=on + backend yok → komut çalıştırılmamalı."""
    from ajanox.core import primitives

    monkeypatch.setenv("AJANOX_SANDBOX", "on")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "none")

    called = {"n": 0}

    def fake_run(*a, **kw):
        called["n"] += 1
        raise AssertionError("subprocess.run shouldn't be called when blocked")

    monkeypatch.setattr(primitives.subprocess, "run", fake_run)
    out = primitives.bash("echo hi")
    assert called["n"] == 0
    assert out.startswith("Hata: sandbox bloğu")


def test_bash_network_perm_passed_to_sandbox(monkeypatch):
    """network_read permission'ı --share-net olarak sandbox argv'sine geçer."""
    from ajanox.core import primitives

    monkeypatch.setenv("AJANOX_SANDBOX", "auto")
    monkeypatch.setattr(sandbox, "detect_backend", lambda: "bwrap")
    token = primitives.ACTIVE_PERMISSIONS.set(
        frozenset({"shell_unsafe", "network_read"})
    )

    captured: dict = {}

    class _FakeResult:
        stdout = ""
        stderr = ""
        returncode = 0

    monkeypatch.setattr(
        primitives.subprocess,
        "run",
        lambda argv, **kw: captured.update(argv=argv) or _FakeResult(),
    )
    try:
        primitives.bash("curl https://example.com")
    finally:
        primitives.ACTIVE_PERMISSIONS.reset(token)

    assert "--share-net" in captured["argv"]
    assert "--unshare-net" not in captured["argv"]
