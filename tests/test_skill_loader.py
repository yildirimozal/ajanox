"""Skill loader testleri."""

from pathlib import Path

from ajanox.core.skill_loader import (
    format_skill_catalog,
    load_skill_catalog,
    parse_frontmatter,
)


def test_parse_frontmatter_basic():
    text = """---
name: test
version: 1.0.0
description: A test skill
---
# Body"""
    fm = parse_frontmatter(text)
    assert fm["name"] == "test"
    assert fm["version"] == "1.0.0"
    assert fm["description"] == "A test skill"


def test_parse_frontmatter_quoted_values():
    text = '---\nname: "quoted"\ndesc: \'single\'\n---\n'
    fm = parse_frontmatter(text)
    assert fm["name"] == "quoted"
    assert fm["desc"] == "single"


def test_parse_frontmatter_no_frontmatter():
    assert parse_frontmatter("# Just a header") == {}


def test_load_real_skills():
    """skills/ klasöründeki gerçek SKILL.md'leri yüklemeyi dene."""
    pkg_root = Path(__file__).resolve().parents[1]
    skills_dir = pkg_root / "skills"
    catalog = load_skill_catalog(skills_dir)
    names = {s.name for s in catalog}
    assert "weather" in names
    assert "find-large-files" in names
    assert "mac-notification" in names


def test_load_zip_folder_skill():
    """zip-folder skill'inin doğru yüklendiğini doğrular."""
    pkg_root = Path(__file__).resolve().parents[1]
    skills_dir = pkg_root / "skills"
    catalog = load_skill_catalog(skills_dir)
    skill = next((s for s in catalog if s.name == "zip-folder"), None)
    assert skill is not None, "zip-folder skill yüklenemedi"
    assert "zip" in skill.description.lower() or "yedek" in skill.description.lower()
    assert skill.requires_os == ("linux", "darwin")


def test_load_parses_requires_os_and_network_domains(tmp_path):
    skill_dir = tmp_path / "netskill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: netskill\n"
        "description: weather via api\n"
        "version: 0.1.0\n"
        "permissions: [network_read]\n"
        "requires:\n"
        "  os: [linux, darwin]\n"
        "network:\n"
        "  allowed_domains: [wttr.in, API.OpenWeatherMap.org]\n"
        "---\n# body",
        encoding="utf-8",
    )
    catalog = load_skill_catalog(tmp_path)
    skill = next(s for s in catalog if s.name == "netskill")
    assert skill.requires_os == ("linux", "darwin")
    # domain'ler lowercase normalize edilir
    assert skill.network_domains == ("wttr.in", "api.openweathermap.org")


def test_load_no_network_section_empty_domains(tmp_path):
    skill_dir = tmp_path / "plain"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: plain\ndescription: x\npermissions: [shell_safe]\n---\n# b",
        encoding="utf-8",
    )
    catalog = load_skill_catalog(tmp_path)
    skill = next(s for s in catalog if s.name == "plain")
    assert skill.network_domains == ()
    assert skill.requires_os == ()


def test_format_catalog():
    from ajanox.core.skill_loader import Skill

    catalog = [Skill(name="foo", description="bar", location="/x")]
    output = format_skill_catalog(catalog)
    assert "<skill>" in output
    assert "<name>foo</name>" in output


def test_format_empty_catalog():
    assert format_skill_catalog([]) == ""
