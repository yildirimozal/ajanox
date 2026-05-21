"""`ajanox skill` CLI testleri."""

import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest

from ajanox.cli.skill import run


@pytest.fixture
def isolated_skills_dir(tmp_path, monkeypatch):
    """skills/ dizinini tmp'a yönlendir + builtin path'i de izole et."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AJANOX_HOME", str(tmp_path / ".ajanox"))
    # Dev fallback repo root'taki skills'i bulmasın — tmp_path altında yok-olan yola yönlendir
    nonexistent = tmp_path / "_no_builtin"
    monkeypatch.setattr("ajanox.cli.skill._builtin_skills_dir", lambda: nonexistent)
    return tmp_path


def test_init_creates_skill_with_description(isolated_skills_dir):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = run(["init", "merhaba", "--description", "Merhaba der"])
    assert rc == 0
    skill_md = isolated_skills_dir / "skills" / "merhaba" / "SKILL.md"
    assert skill_md.exists()
    content = skill_md.read_text(encoding="utf-8")
    assert "name: merhaba" in content
    assert "Merhaba der" in content
    assert "shell_safe" in content


def test_init_user_flag_writes_to_user_dir(isolated_skills_dir):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = run(["init", "kullanici-skill", "--user", "--description", "test"])
    assert rc == 0
    assert (
        isolated_skills_dir / ".ajanox" / "skills" / "kullanici-skill" / "SKILL.md"
    ).exists()


def test_init_rejects_invalid_name(isolated_skills_dir):
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run(["init", "Bad_Name", "--description", "x"])
    assert rc == 1
    assert "kebab-case" in err.getvalue()


def test_init_rejects_existing_skill(isolated_skills_dir):
    run(["init", "duplicate", "--description", "x"])
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run(["init", "duplicate", "--description", "y"])
    assert rc == 1
    assert "zaten var" in err.getvalue()


def test_check_valid_skill(isolated_skills_dir):
    run(["init", "valid-skill", "--description", "test"])
    out = io.StringIO()
    with redirect_stdout(out):
        rc = run(["check", "skills/valid-skill"])
    assert rc == 0
    output = out.getvalue()
    assert "✓" in output or "uyarı" in output  # body önerileri uyarı verebilir


def test_check_missing_required_field(isolated_skills_dir):
    bad_skill = isolated_skills_dir / "bad" / "SKILL.md"
    bad_skill.parent.mkdir()
    bad_skill.write_text(
        "---\nname: bad\n---\n# body", encoding="utf-8"
    )
    out = io.StringIO()
    with redirect_stdout(out):
        rc = run(["check", str(bad_skill)])
    assert rc == 1
    assert "Eksik zorunlu alan" in out.getvalue()


def test_check_forbidden_permission(isolated_skills_dir):
    bad_skill = isolated_skills_dir / "sudo-skill" / "SKILL.md"
    bad_skill.parent.mkdir()
    bad_skill.write_text(
        """---
name: sudo-skill
version: 0.1.0
description: bad skill with sudo
ajanox: ">=0.2.0 <1.0.0"
permissions: [sudo]
---
# body""",
        encoding="utf-8",
    )
    out = io.StringIO()
    with redirect_stdout(out):
        rc = run(["check", str(bad_skill)])
    assert rc == 1
    output = out.getvalue()
    assert "YASAK" in output and "sudo" in output


def test_check_unknown_permission_is_warning(isolated_skills_dir):
    bad_skill = isolated_skills_dir / "weird" / "SKILL.md"
    bad_skill.parent.mkdir()
    bad_skill.write_text(
        """---
name: weird
version: 0.1.0
description: x
ajanox: ">=0.2.0 <1.0.0"
permissions: [shell_safe, made_up_perm]
---
# body""",
        encoding="utf-8",
    )
    out = io.StringIO()
    with redirect_stdout(out):
        rc = run(["check", str(bad_skill)])
    # warning ama error değil → 0
    assert rc == 0
    assert "Bilinmeyen permission" in out.getvalue()


def test_check_path_not_found(isolated_skills_dir):
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run(["check", "nonexistent/SKILL.md"])
    assert rc == 1


def test_list_empty(isolated_skills_dir):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = run(["list"])
    assert rc == 0
    assert "Yüklü skill yok" in out.getvalue()


def test_list_shows_skills(isolated_skills_dir):
    run(["init", "skill-bir", "--description", "test bir"])
    run(["init", "skill-iki", "--description", "test iki"])
    out = io.StringIO()
    with redirect_stdout(out):
        rc = run(["list"])
    assert rc == 0
    output = out.getvalue()
    assert "skill-bir" in output
    assert "skill-iki" in output
    assert "shell_safe" in output


def test_migrate_is_stub(isolated_skills_dir):
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run(["migrate"])
    assert rc == 0
    assert "TODO" in err.getvalue()


def test_no_args_shows_help():
    out = io.StringIO()
    with redirect_stdout(out):
        rc = run([])
    assert rc == 1
