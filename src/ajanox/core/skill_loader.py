"""SKILL.md katalog yükleyici.

Spec: docs/SPEC.md (v0.1)
Lazy-load: katalog için sadece frontmatter (name, description) yüklenir;
gövde model SKILL.md'yi read_file ile okuduğunda gelir.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Skill:
    name: str
    description: str
    location: str
    version: str = "0.0.0"
    permissions: tuple[str, ...] = ()
    icon: str = ""           # emoji veya path; UI'da göster
    example_prompt: str = "" # tıklanınca gönderilen örnek komut
    requires_os: tuple[str, ...] = ()  # boş = her platform


def parse_frontmatter(text: str) -> dict[str, Any]:
    """SKILL.md başındaki YAML frontmatter'ı parse et.

    Format:
        ---
        key: value
        nested:
          subkey: value
        list_field: [a, b, c]
        ---
        # body...
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    raw = text[3:end].strip()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def load_skill_catalog(skills_dir: Path) -> list[Skill]:
    """skills/ altındaki tüm SKILL.md'leri katalog olarak yükle."""
    catalog: list[Skill] = []
    if not skills_dir.exists():
        return catalog

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue

        fm = parse_frontmatter(text)
        name = str(fm.get("name", "")).strip()
        desc = str(fm.get("description", "")).strip()
        if not name or not desc:
            continue

        perms_raw = fm.get("permissions") or []
        permissions = (
            tuple(str(p) for p in perms_raw) if isinstance(perms_raw, list) else ()
        )

        requires_raw = (fm.get("requires") or {}).get("os") if isinstance(fm.get("requires"), dict) else None
        requires_os = (
            tuple(str(o).strip().lower() for o in requires_raw)
            if isinstance(requires_raw, list)
            else ()
        )

        catalog.append(
            Skill(
                name=name,
                description=desc,
                location=str(skill_md.resolve()),
                version=str(fm.get("version", "0.0.0")),
                permissions=permissions,
                icon=str(fm.get("icon", "")).strip(),
                example_prompt=str(fm.get("example_prompt", "")).strip(),
                requires_os=requires_os,
            )
        )
    return catalog


def format_skill_catalog(catalog: list[Skill]) -> str:
    """Sistem promptuna eklenecek XML benzeri katalog (OpenClaw stili)."""
    if not catalog:
        return ""
    lines = [
        "",
        "Aşağıda kullanabileceğin skill'ler var. Kullanıcının isteği bir skill'in",
        "description'ı ile eşleşiyorsa: ÖNCE `read_file` tool'u ile `location` yolunu",
        "oku, SONRA içindeki komutu `bash` tool'u ile çalıştır.",
        "",
        "<available_skills>",
    ]
    for skill in catalog:
        lines += [
            "  <skill>",
            f"    <name>{skill.name}</name>",
            f"    <description>{skill.description}</description>",
            f"    <location>{skill.location}</location>",
            "  </skill>",
        ]
    lines.append("</available_skills>")
    return "\n".join(lines)
