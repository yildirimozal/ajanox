"""Doğal dil shell — Ajanox'un birincil arayüzü."""

from __future__ import annotations

import os
from pathlib import Path

from .. import __version__
from ..core.agent import DEFAULT_MODEL, check_ollama_health, run_agent
from ..core.compat import check_skill
from ..core.platform import current_os, describe, supports_skill_os
from ..core.skill_loader import Skill, load_skill_catalog


def _builtin_skills_dir() -> Path:
    """Paket içi skill'ler.

    İki kurulum modu desteklenir:
      1. Wheel install (`pip install ajanox`): force-include ile
         site-packages/ajanox/builtin_skills/ altında bulunur
      2. Dev/editable install (`pip install -e .`): yukarıdaki yol yok;
         repo root'taki skills/ klasörüne fallback yap
    """
    pkg_dir = Path(__file__).resolve().parent.parent  # site-packages/ajanox veya src/ajanox
    wheel_path = pkg_dir / "builtin_skills"
    if wheel_path.exists():
        return wheel_path
    # Dev fallback: src/ajanox → src → repo_root → repo_root/skills
    dev_path = pkg_dir.parent.parent / "skills"
    return dev_path


def _project_skills_dir() -> Path:
    """Geliştirme modu: cwd/skills/ — repo'dan çalıştırırken görünür."""
    return Path.cwd() / "skills"


def _user_skills_dir() -> Path:
    """Kullanıcı skill'leri: ~/.ajanox/skills/"""
    return Path(os.environ.get("AJANOX_HOME", str(Path.home() / ".ajanox"))) / "skills"


def _filter_compatible(catalog: list[Skill]) -> tuple[list[Skill], list[str]]:
    """Geçerli platform + Ajanox sürümüyle uyumsuz skill'leri ayır.

    Returns: (uyumlu_skill'ler, atlanan_skill_açıklamaları)
    """
    compatible: list[Skill] = []
    skipped: list[str] = []
    for s in catalog:
        if not supports_skill_os(list(s.requires_os)):
            skipped.append(f"{s.name} (requires OS: {', '.join(s.requires_os)})")
            continue
        ok, reason = check_skill(s.ajanox_constraint, __version__)
        if not ok:
            skipped.append(f"{s.name} ({reason})")
            continue
        compatible.append(s)
    return compatible, skipped


def _collect_skills() -> tuple[list[Skill], list[str], list[str]]:
    """Tüm kaynaklardan skill'leri topla; (catalog, source_labels, skipped) döner.

    Override: AJANOX_SKILLS_DIR env varsa SADECE o yol kullanılır.
    Geçerli platformla uyumsuz skill'ler katalogdan çıkarılır.
    """
    override = os.environ.get("AJANOX_SKILLS_DIR")
    if override:
        loaded = load_skill_catalog(Path(override))
        compatible, skipped = _filter_compatible(loaded)
        return compatible, [override], skipped

    catalog: list[Skill] = []
    sources: list[str] = []
    for source_path in (
        _builtin_skills_dir(),
        _project_skills_dir(),
        _user_skills_dir(),
    ):
        if source_path.exists():
            loaded = load_skill_catalog(source_path)
            if loaded:
                catalog.extend(loaded)
                sources.append(str(source_path))
    compatible, skipped = _filter_compatible(catalog)
    return compatible, sources, skipped


def run() -> int:
    catalog, sources, skipped = _collect_skills()
    model = os.environ.get("AJANOX_MODEL", DEFAULT_MODEL)

    print(f"Ajanox v{__version__} — model: {model} — platform: {describe()}")

    # Ön gereksinim kontrolü — Ollama + model
    ok, health_msg = check_ollama_health(model)
    print(health_msg)
    if not ok:
        print(
            "\n⚠️  Ajanox şu anda çalışamaz. Yukarıdaki adımları tamamlayıp\n"
            "    `ajanox` komutunu tekrar çalıştır."
        )
        return 1

    print(f"Yüklü skill sayısı: {len(catalog)}")
    for src in sources:
        print(f"  kaynak: {src}")
    for s in catalog:
        print(f"  - {s.name} (v{s.version}): {s.description}")
    if not catalog:
        print("  (henüz skill yok — 'ajanox skill init <name>' ile başla)")
    if skipped:
        print(f"  ({len(skipped)} skill bu platformda atlandı: {'; '.join(skipped)})")
    print("Çıkmak için 'q' yaz, konuşmayı sıfırlamak için '/reset'.\n")

    history: list[dict] = []  # multi-turn conversation state (sliding window)

    while True:
        try:
            user_input = input("Sen: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in ("q", "quit", "exit", "çık"):
            break
        if user_input.lower() in ("/reset", "/yeni", "/clear"):
            history = []
            print("✓ Konuşma sıfırlandı.\n")
            continue
        history = run_agent(user_input, catalog, history=history, model=model)
    return 0
