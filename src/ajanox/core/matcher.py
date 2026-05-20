"""Deterministik skill matching.

Modelin "katalogdaki hangi skill?" kararını Python tarafına çekiyoruz —
LLM bu işte güvenilmez (smoke testte gözlemlendi: model bazen skill ismini
tool olarak çağırıyor, bazen reddediyor). Basit keyword matching genellikle
yeterli; ileride embedding similarity'ye yükseltilebilir.

Strateji:
  1. Kullanıcı girdisinden ve her skill'in description + tag'lerinden
     anahtar kelime kümeleri çıkar.
  2. Türkçe stop-word'leri eler.
  3. En çok kelime kesişimi olan skill'i öner.
  4. Bir skill seçilince agent loop'a "UYGUN SKILL: X" hint'i geçer.
"""

from __future__ import annotations

import re

from .skill_loader import Skill


# Türkçe + İngilizce yaygın stop-word'ler. Skill seçimine katkı sağlamayan kelimeler.
STOP_WORDS = frozenset(
    {
        # Türkçe
        "bir", "bu", "şu", "o", "ne", "nasıl", "nedir", "nerede", "nereden",
        "için", "ile", "ama", "de", "da", "ki", "mi", "mı", "mu", "mü",
        "var", "yok", "olur", "olmak", "ben", "sen", "biz", "siz", "onlar",
        "bana", "sana", "ona", "bize", "size", "onlara",
        "bul", "göster", "yap", "yapar", "et", "eder", "gönder", "söyle",
        "lütfen", "rica", "ederim", "merhaba", "selam",
        "klasör", "klasörü", "klasördeki", "klasörde", "klasörün",
        "dosya", "dosyalar", "dosyaları", "dosyalarını",
        "ve", "veya", "değil", "ise", "eğer",
        "kaç", "kim", "hangi",
        # İngilizce
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "in", "on", "at", "to", "for", "of", "with", "by",
        "and", "or", "but", "not",
        "i", "you", "he", "she", "it", "we", "they",
        "do", "does", "did", "have", "has", "had",
        "what", "where", "when", "who", "how", "why",
    }
)

_TOKEN_PATTERN = re.compile(r"[\wçğıöşüÇĞİÖŞÜ]+", re.UNICODE)


def _tokenize(text: str) -> set[str]:
    """Türkçe karakterleri koruyarak kelime tokenları çıkar, stop-word'leri ele."""
    if not text:
        return set()
    tokens = (m.group().lower() for m in _TOKEN_PATTERN.finditer(text))
    return {t for t in tokens if t not in STOP_WORDS and len(t) > 1}


def _skill_keywords(skill: Skill) -> set[str]:
    """Bir skill'in description'ından keyword kümesi çıkar.

    İleride tags + name + örnek prompt'lar eklenebilir.
    """
    return _tokenize(skill.description) | _tokenize(skill.name.replace("-", " "))


def _overlap_score(user_tokens: set[str], skill_tokens: set[str]) -> int:
    """Türkçe ek tolerantlı overlap. Exact match veya 4+ harf prefix match."""
    score = 0
    for u in user_tokens:
        if u in skill_tokens:
            score += 1
            continue
        # Türkçe ek toleransı: 4+ karakterli kelime, prefix eşleşmesi
        if len(u) >= 4:
            for s in skill_tokens:
                if len(s) >= 4 and (u.startswith(s) or s.startswith(u)):
                    score += 1
                    break
    return score


def find_best_match(
    user_input: str,
    catalog: list[Skill],
    context: str = "",
) -> tuple[Skill | None, int]:
    """Kullanıcı girdisine en uygun skill'i (varsa) ve overlap skorunu döner.

    Args:
        user_input: bu turdaki kullanıcı mesajı
        catalog: yüklü skill'ler
        context: önceki turn'lerden conversation context (opsiyonel).
            Multi-turn senaryoda "evet sil" gibi kısa girdilerde önceki
            turn'lerde geçen skill'in adı/desc'i match'i kuvvetlendirir.

    Eşik: en az 1 kelime kesişimi. Hiçbiri eşleşmezse (None, 0).
    """
    if not catalog:
        return None, 0

    user_tokens = _tokenize(user_input)
    # Context tokenları daha düşük ağırlıkta sayılır ama yine de score'a katkı
    context_tokens = _tokenize(context)
    combined = user_tokens | context_tokens
    if not combined:
        return None, 0

    best_skill: Skill | None = None
    best_score = 0
    for skill in catalog:
        score = _overlap_score(combined, _skill_keywords(skill))
        if score > best_score:
            best_score = score
            best_skill = skill

    return best_skill, best_score


def format_match_hint(skill: Skill) -> str:
    """Agent loop, bir skill match'i bulduğunda system prompt'a bunu ekler."""
    return f"""
=== UYGUN SKILL TESPİT EDİLDİ ===
İSİM: {skill.name}
LOCATION: {skill.location}
AÇIKLAMA: {skill.description}

Bu skill kullanıcı isteğine UYGUN. Şu sırayı izle:
  1. `read_file` tool'u ile yukarıdaki LOCATION yolunu oku.
  2. SKILL.md içindeki bash komutunu `bash` tool'u ile çalıştır.
  3. Çıktıyı kullanıcıya doğal Türkçe ile aktar.
"""
