"""Doğal dil shell — Ajanox'un birincil arayüzü."""

from __future__ import annotations

import os
from pathlib import Path

from ..core.agent import DEFAULT_MODEL, run_agent
from ..core.skill_loader import load_skill_catalog


def _default_skills_dir() -> Path:
    """Skill dizinini bul. Geliştirme: paket altındaki skills/.
    İleride: ~/.ajanox/skills/ veya XDG paths."""
    pkg_root = Path(__file__).resolve().parents[3]
    return pkg_root / "skills"


def run() -> int:
    skills_dir = Path(os.environ.get("AJANOX_SKILLS_DIR", str(_default_skills_dir())))
    catalog = load_skill_catalog(skills_dir)
    model = os.environ.get("AJANOX_MODEL", DEFAULT_MODEL)

    print(f"Ajanox v0.1 — model: {model}")
    print(f"Yüklü skill sayısı: {len(catalog)} (kaynak: {skills_dir})")
    for s in catalog:
        print(f"  - {s.name} (v{s.version}): {s.description}")
    if not catalog:
        print("  (skills/ klasörü boş veya yok)")
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
