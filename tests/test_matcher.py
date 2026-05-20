"""Deterministik skill matcher testleri."""

import pytest

from ajanox.core.matcher import find_best_match, format_match_hint
from ajanox.core.skill_loader import Skill


@pytest.fixture
def catalog() -> list[Skill]:
    return [
        Skill(
            name="weather",
            description="Bir şehrin güncel hava durumunu söyler.",
            location="/x/weather",
        ),
        Skill(
            name="find-large-files",
            description="Bir klasördeki en büyük dosyaları ve alt klasörleri listeler.",
            location="/x/flf",
        ),
        Skill(
            name="mac-notification",
            description="macOS'ta masaüstü bildirimi gösterir.",
            location="/x/mac",
        ),
    ]


def test_weather_query_matches_weather(catalog):
    skill, score = find_best_match("İstanbul'da hava nasıl?", catalog)
    assert skill is not None
    assert skill.name == "weather"
    assert score >= 1


def test_large_files_query(catalog):
    skill, score = find_best_match(
        "Downloads klasöründeki en büyük dosyaları bul", catalog
    )
    assert skill is not None
    assert skill.name == "find-large-files"


def test_notification_query_with_turkish_suffix(catalog):
    # 'bildirim' (kullanıcı) vs 'bildirimi' (description) — Türkçe ek toleransı
    skill, score = find_best_match("Bana bir bildirim yolla", catalog)
    assert skill is not None
    assert skill.name == "mac-notification"


def test_unrelated_query_returns_none(catalog):
    skill, score = find_best_match("Selam nasılsın?", catalog)
    assert skill is None
    assert score == 0


def test_empty_input(catalog):
    assert find_best_match("", catalog) == (None, 0)


def test_empty_catalog():
    assert find_best_match("hava durumu", []) == (None, 0)


def test_multi_word_overlap_wins(catalog):
    """'Ankara hava durumu' = 2 kelime weather'a hit, daha yüksek skor."""
    skill, score = find_best_match("Ankara hava durumu", catalog)
    assert skill is not None
    assert skill.name == "weather"
    assert score >= 2


def test_format_match_hint(catalog):
    hint = format_match_hint(catalog[0])
    assert "UYGUN SKILL TESPİT EDİLDİ" in hint
    assert "weather" in hint
    assert "/x/weather" in hint
