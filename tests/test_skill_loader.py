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


def test_format_catalog():
    from ajanox.core.skill_loader import Skill

    catalog = [Skill(name="foo", description="bar", location="/x")]
    output = format_skill_catalog(catalog)
    assert "<skill>" in output
    assert "<name>foo</name>" in output


def test_format_empty_catalog():
    assert format_skill_catalog([]) == ""
