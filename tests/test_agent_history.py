"""Multi-turn conversation history testleri.

run_agent gerçek LLM çağrısı yaptığı için bunlar ya `_trimmed` helper'ını
veya chat() mock'lanmış halini test eder.
"""

from ajanox.core.agent import _trimmed


def test_trimmed_empty_history():
    result = _trimmed([], "merhaba", "selam", limit=10)
    assert result == [
        {"role": "user", "content": "merhaba"},
        {"role": "assistant", "content": "selam"},
    ]


def test_trimmed_no_assistant_response():
    # Boş yanıt → sadece user message eklenir
    result = _trimmed([], "merhaba", "", limit=10)
    assert result == [{"role": "user", "content": "merhaba"}]


def test_trimmed_appends_to_prior():
    prior = [
        {"role": "user", "content": "ilk soru"},
        {"role": "assistant", "content": "ilk cevap"},
    ]
    result = _trimmed(prior, "ikinci", "ikinci cevap", limit=10)
    assert len(result) == 4
    assert result[0]["content"] == "ilk soru"
    assert result[-1]["content"] == "ikinci cevap"


def test_trimmed_sliding_window_limit():
    # 10 message dolu, yeni turn 2 ekler → en eski 2 düşer
    prior = []
    for i in range(5):
        prior.append({"role": "user", "content": f"u{i}"})
        prior.append({"role": "assistant", "content": f"a{i}"})
    assert len(prior) == 10
    result = _trimmed(prior, "u5", "a5", limit=10)
    assert len(result) == 10
    # En eski olan u0/a0 düşmüş olmalı
    assert result[0]["content"] == "u1"
    assert result[-1]["content"] == "a5"


def test_trimmed_zero_limit_keeps_all():
    prior = [{"role": "user", "content": f"u{i}"} for i in range(20)]
    result = _trimmed(prior, "yeni", "cevap", limit=0)
    assert len(result) == 22
