"""run_agent döngü testleri — chat_stream mock'lanır, Ollama'ya gidilmez."""

import json

import pytest

from ajanox.core import agent, approval


@pytest.fixture(autouse=True)
def auto_approve():
    approval.set_auto_approve(True)
    approval.reset_session()
    yield
    approval.set_auto_approve(False)


class FakeChat:
    """chat_stream yerine geçer; scripted yanıtları sırayla döner, mesajları kaydeder."""

    def __init__(self, scripted):
        self.scripted = list(scripted)
        self.calls: list[list[dict]] = []

    def __call__(self, messages, model=None, on_chunk=None):
        self.calls.append([dict(m) for m in messages])
        content = self.scripted.pop(0) if self.scripted else "bitti"
        return {"role": "assistant", "content": content}


def _tc(name, **args) -> str:
    return f'<tool_call>{json.dumps({"name": name, "arguments": args})}</tool_call>'


def _run(monkeypatch, scripted, **kwargs):
    fake = FakeChat(scripted)
    monkeypatch.setattr(agent, "chat_stream", fake)
    events: list[dict] = []
    history = agent.run_agent(
        kwargs.pop("user_input", "merhaba"),
        kwargs.pop("catalog", []),
        on_event=events.append,
        **kwargs,
    )
    return fake, events, history


def test_normal_tool_then_final(monkeypatch):
    _fake, events, history = _run(
        monkeypatch, [_tc("bash", command="echo hi"), "İşte: hi"]
    )
    finals = [e for e in events if e["type"] == "final"]
    assert finals and finals[-1]["content"] == "İşte: hi"
    assert any(e["type"] == "tool_result" and "hi" in e["output"] for e in events)
    assert history[-1] == {"role": "assistant", "content": "İşte: hi"}


def test_denied_tool_emits_denied(monkeypatch):
    # rm shell_unsafe — default sistem izinleri (shell_safe, file_read) reddeder
    _fake, events, _ = _run(
        monkeypatch, [_tc("bash", command="rm -rf /tmp/x"), "tamam"]
    )
    assert any(e["type"] == "denied" for e in events)


def test_unknown_tool_emits_warn(monkeypatch):
    _fake, events, _ = _run(monkeypatch, [_tc("frobnicate"), "tamam"])
    assert any(e["type"] == "warn" and "frobnicate" in e["message"] for e in events)


def test_invalid_tool_call_rejected(monkeypatch):
    # bash command boş → verify_tool_call reddeder (enforce'tan önce)
    _fake, events, _ = _run(monkeypatch, [_tc("bash", command=""), "tamam"])
    assert any(e["type"] == "warn" and "boş" in e["message"] for e in events)


def test_max_iter_fallback(monkeypatch):
    calls = {"n": 0}

    def always_tool(messages, model=None, on_chunk=None):
        calls["n"] += 1
        return {"role": "assistant", "content": _tc("bash", command="echo x")}

    monkeypatch.setattr(agent, "chat_stream", always_tool)
    events: list[dict] = []
    agent.run_agent("x", [], max_iter=2, on_event=events.append)
    finals = [e for e in events if e["type"] == "final"]
    assert finals and "tamamlayamad" in finals[-1]["content"]
    assert calls["n"] == 2  # tam max_iter kez döndü


def test_skill_md_followup_injected(monkeypatch):
    fake, _events, _ = _run(
        monkeypatch, [_tc("read_file", path="/tmp/x/SKILL.md"), "okudum"]
    )
    # İkinci chat çağrısının mesajlarında SKILL.md takip talimatı olmalı
    assert len(fake.calls) >= 2
    assert any(
        "SKILL.md içeriğini aldın" in m.get("content", "") for m in fake.calls[1]
    )
