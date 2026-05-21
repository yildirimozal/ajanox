"""Doğal dil shell — Ajanox'un birincil arayüzü."""

from __future__ import annotations

import os
from pathlib import Path

from .. import __version__
from ..core.agent import DEFAULT_MODEL, check_ollama_health, run_agent
from ..core.skill_loader import Skill, load_skill_catalog


def _builtin_skills_dir() -> Path:
    """Paket içi (pip install ile gelen) skill'ler — site-packages/ajanox/builtin_skills."""
    return Path(__file__).resolve().parent.parent / "builtin_skills"


def _project_skills_dir() -> Path:
    """Geliştirme modu: cwd/skills/ — repo'dan çalıştırırken görünür."""
    return Path.cwd() / "skills"


def _user_skills_dir() -> Path:
    """Kullanıcı skill'leri: ~/.ajanox/skills/"""
    return Path(os.environ.get("AJANOX_HOME", str(Path.home() / ".ajanox"))) / "skills"


def _collect_skills() -> tuple[list[Skill], list[str]]:
    """Tüm kaynaklardan skill'leri topla; (catalog, source_labels) döner.

    Override: AJANOX_SKILLS_DIR env varsa SADECE o yol kullanılır.
    """
    override = os.environ.get("AJANOX_SKILLS_DIR")
    if override:
        return load_skill_catalog(Path(override)), [override]

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
    return catalog, sources


def run() -> int:
    catalog, sources = _collect_skills()
    model = os.environ.get("AJANOX_MODEL", DEFAULT_MODEL)

    print(f"Ajanox v{__version__} — model: {model}")

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
