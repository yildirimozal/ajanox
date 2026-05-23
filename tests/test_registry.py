"""Skill registry testleri."""


import pytest

from ajanox.core import registry as reg


def test_registry_repo_path():
    r = reg.Registry(name="x", url="https://github.com/yildirimozal/miniagent")
    assert r.repo_path == "yildirimozal/miniagent"


def test_registry_repo_path_with_git_suffix():
    r = reg.Registry(name="x", url="https://github.com/foo/bar.git")
    assert r.repo_path == "foo/bar"


def test_registry_skill_md_url():
    r = reg.Registry(name="m", url="https://github.com/u/r", branch="dev")
    assert r.skill_md_url("weather") == (
        "https://raw.githubusercontent.com/u/r/dev/skills/weather/SKILL.md"
    )


def test_registry_invalid_url_raises():
    r = reg.Registry(name="bad", url="not-a-url")
    with pytest.raises(ValueError, match="Geçersiz GitHub URL"):
        _ = r.repo_path


def test_resolve_bare_name_uses_default_registry():
    regs = [
        reg.Registry(name="r1", url="https://github.com/x/y", default=True),
        reg.Registry(name="r2", url="https://github.com/a/b"),
    ]
    spec = reg.resolve_spec("foo", regs)
    assert spec.name == "foo"
    assert spec.registry.name == "r1"
    assert "x/y/main/skills/foo/SKILL.md" in spec.raw_url


def test_resolve_bare_name_first_registry_when_no_default():
    regs = [reg.Registry(name="only", url="https://github.com/a/b")]
    spec = reg.resolve_spec("foo", regs)
    assert spec.registry.name == "only"


def test_resolve_bare_name_no_registry_raises():
    with pytest.raises(ValueError, match="Default registry yok"):
        reg.resolve_spec("foo", [])


def test_resolve_shorthand():
    spec = reg.resolve_spec("yildirimozal/miniagent:open-ports", [])
    assert spec.name == "open-ports"
    assert spec.registry.repo_path == "yildirimozal/miniagent"


def test_resolve_full_tree_url():
    url = "https://github.com/x/y/tree/main/skills/foo"
    spec = reg.resolve_spec(url, [])
    assert spec.name == "foo"
    assert spec.registry.branch == "main"
    assert spec.raw_url.endswith("/main/skills/foo/SKILL.md")


def test_resolve_raw_url():
    url = "https://raw.githubusercontent.com/x/y/dev/skills/bar/SKILL.md"
    spec = reg.resolve_spec(url, [])
    assert spec.name == "bar"
    assert spec.registry.branch == "dev"
    assert spec.raw_url == url


def test_resolve_invalid_raises():
    with pytest.raises(ValueError, match="Geçersiz skill spec"):
        reg.resolve_spec("INVALID-with-CAPS", [])


def test_default_registries_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AJANOX_HOME", str(tmp_path / ".ajanox"))
    regs = reg.load_registries()
    assert len(regs) >= 1
    assert any(r.name == "miniagent" for r in regs)


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("AJANOX_HOME", str(tmp_path / ".ajanox"))
    custom = [reg.Registry(name="my", url="https://github.com/a/b", default=True)]
    reg.save_registries(custom)
    loaded = reg.load_registries()
    assert len(loaded) == 1
    assert loaded[0].name == "my"
    assert loaded[0].default


def test_install_and_remove_skill(tmp_path, monkeypatch):
    monkeypatch.setenv("AJANOX_HOME", str(tmp_path / ".ajanox"))
    content = "---\nname: test-skill\nversion: 0.1.0\ndescription: test\n---\n# body"
    path = reg.install_skill_md("test-skill", content)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == content

    assert reg.remove_user_skill("test-skill") is True
    assert reg.remove_user_skill("test-skill") is False  # 2. seferinde yok


def test_fetch_skill_md_rejects_non_yaml(monkeypatch):
    """Frontmatter ile başlamayan içeriği reddetmeli."""
    def fake_urlopen(req, timeout):
        class FakeResp:
            def read(self):
                return b"# Bu sadece markdown, frontmatter yok"
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
        return FakeResp()
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(ValueError, match="frontmatter"):
        reg.fetch_skill_md("https://x.test/SKILL.md")
