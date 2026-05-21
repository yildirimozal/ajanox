"""Skill registry — GitHub-tabanlı uzak skill kaynakları.

Bir registry, GitHub'daki bir repo'da `skills/<name>/SKILL.md` yapısı bekler:
    https://github.com/<user>/<repo>/tree/<branch>/skills/<name>/

Default kayıtlı registry: `yildirimozal/miniagent`.

Kullanıcının kayıt dosyası: `~/.ajanox/registries.json`
"""

from __future__ import annotations

import json
import os
import re
import shutil
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


_AJANOX_HOME = lambda: Path(os.environ.get("AJANOX_HOME", str(Path.home() / ".ajanox")))


def _registries_file() -> Path:
    return _AJANOX_HOME() / "registries.json"


def _user_skills_dir() -> Path:
    return _AJANOX_HOME() / "skills"


DEFAULT_REGISTRIES = [
    {
        "name": "miniagent",
        "url": "https://github.com/yildirimozal/miniagent",
        "branch": "main",
        "default": True,
    },
]


@dataclass
class Registry:
    name: str
    url: str  # https://github.com/USER/REPO
    branch: str = "main"
    default: bool = False

    @property
    def repo_path(self) -> str:
        m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", self.url)
        if not m:
            raise ValueError(f"Geçersiz GitHub URL: {self.url}")
        return f"{m.group(1)}/{m.group(2)}"

    def skill_md_url(self, skill_name: str) -> str:
        return (
            f"https://raw.githubusercontent.com/{self.repo_path}/"
            f"{self.branch}/skills/{skill_name}/SKILL.md"
        )

    def list_skills_api_url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.repo_path}/contents/skills"
            f"?ref={self.branch}"
        )


@dataclass
class SkillSpec:
    name: str
    registry: Optional[Registry]
    raw_url: str


# Pattern'ler
_FULL_TREE_URL = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/skills/([^/?#]+)/?$"
)
_RAW_URL = re.compile(
    r"^https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/skills/([^/]+)/SKILL\.md$"
)
_SHORTHAND = re.compile(r"^([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+):([a-z][a-z0-9-]*)$")
_BARE_NAME = re.compile(r"^[a-z][a-z0-9-]*$")


def load_registries() -> list[Registry]:
    path = _registries_file()
    if not path.exists():
        return [Registry(**r) for r in DEFAULT_REGISTRIES]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("registries", [])
        return [Registry(**r) for r in items]
    except (json.JSONDecodeError, OSError, TypeError):
        return [Registry(**r) for r in DEFAULT_REGISTRIES]


def save_registries(registries: list[Registry]) -> None:
    path = _registries_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"registries": [asdict(r) for r in registries]}
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def resolve_spec(spec: str, registries: list[Registry]) -> SkillSpec:
    """Bir input string'i çöz: tam URL / shorthand / bare name."""
    spec = spec.strip()

    m = _FULL_TREE_URL.match(spec)
    if m:
        user, repo, branch, name = m.groups()
        r = Registry(name=repo, url=f"https://github.com/{user}/{repo}", branch=branch)
        return SkillSpec(name=name, registry=r, raw_url=r.skill_md_url(name))

    m = _RAW_URL.match(spec)
    if m:
        user, repo, branch, name = m.groups()
        r = Registry(name=repo, url=f"https://github.com/{user}/{repo}", branch=branch)
        return SkillSpec(name=name, registry=r, raw_url=spec)

    m = _SHORTHAND.match(spec)
    if m:
        user, repo, name = m.groups()
        r = Registry(name=repo, url=f"https://github.com/{user}/{repo}")
        return SkillSpec(name=name, registry=r, raw_url=r.skill_md_url(name))

    if _BARE_NAME.match(spec):
        default = next((r for r in registries if r.default), None) or (registries[0] if registries else None)
        if default is None:
            raise ValueError(
                "Default registry yok. Tam URL ya da `user/repo:name` shorthand kullan."
            )
        return SkillSpec(name=spec, registry=default, raw_url=default.skill_md_url(spec))

    raise ValueError(
        f"Geçersiz skill spec: '{spec}'.\n"
        f"  Kabul edilen formatlar:\n"
        f"    • bare-name (örn. open-ports — default registry'den)\n"
        f"    • user/repo:skill\n"
        f"    • https://github.com/user/repo/tree/branch/skills/name"
    )


def fetch_skill_md(url: str, timeout: float = 10.0) -> str:
    """SKILL.md içeriğini indir."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ajanox-skill-installer"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Skill bulunamadı (404): {url}") from e
        raise ValueError(f"HTTP {e.code}: {url}") from e
    except urllib.error.URLError as e:
        raise ValueError(f"Bağlantı hatası: {e.reason}") from e

    if not content.strip().startswith("---"):
        raise ValueError(
            f"İndirilen içerik geçerli bir SKILL.md değil "
            f"(YAML frontmatter `---` ile başlamıyor)"
        )
    return content


def list_registry_skills(registry: Registry, timeout: float = 10.0) -> list[str]:
    """GitHub API ile registry'deki skill klasör isimlerini listele."""
    req = urllib.request.Request(
        registry.list_skills_api_url(),
        headers={"User-Agent": "ajanox-skill-installer", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise ValueError(f"Registry listelenemedi ({registry.name}): {getattr(e, 'reason', e)}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Registry yanıtı JSON değil: {e}") from e

    if not isinstance(data, list):
        raise ValueError(f"Registry yanıtı liste değil: {registry.name}")

    return sorted(item["name"] for item in data if item.get("type") == "dir")


def install_skill_md(name: str, content: str) -> Path:
    """SKILL.md içeriğini ~/.ajanox/skills/<name>/SKILL.md'a yaz."""
    skill_dir = _user_skills_dir() / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(content, encoding="utf-8")
    return skill_md


def remove_user_skill(name: str) -> bool:
    """Kullanıcının skill'ini sil. True = silindi, False = yoktu."""
    skill_dir = _user_skills_dir() / name
    if not skill_dir.exists():
        return False
    shutil.rmtree(skill_dir)
    return True
