"""Approval prompt testleri."""

import pytest

from ajanox.core import approval


@pytest.fixture(autouse=True)
def clean_session():
    approval.reset_session()
    approval.set_auto_approve(False)
    yield
    approval.reset_session()
    approval.set_auto_approve(False)


def test_auto_approve_mode():
    approval.set_auto_approve(True)
    assert approval.request_approval("skill", "bash", "rm x") is True


def test_session_cache_via_t_response(monkeypatch):
    # İlk çağrı: kullanıcı "T"ümü dedi → ikinci çağrı sessiz geçer
    inputs = iter(["t"])
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))
    assert approval.request_approval("skill", "bash", "ls") is True
    # İkinci çağrı: input verilmedi ama session cache'ten True döner
    assert approval.request_approval("skill", "bash", "ls") is True


def test_rejection(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "h")
    assert approval.request_approval("skill", "bash", "rm x") is False


def test_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "e")
    assert approval.request_approval("skill", "bash", "ls") is True


def test_session_cache_disabled_when_allow_session_false(monkeypatch):
    # sudo gibi durumda allow_session=False → her seferinde sor, "T" kabul edilmez
    inputs = iter(["e", "e"])
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))
    # İki çağrı, ikisi de ayrı ayrı "e" istiyor (session yok)
    assert approval.request_approval(
        "skill", "sudo", "x", allow_session=False
    ) is True
    assert approval.request_approval(
        "skill", "sudo", "x", allow_session=False
    ) is True


def test_t_response_rejected_when_session_disabled(monkeypatch):
    # allow_session=False → "T" cevabı session olmadığı için sadece "evet" sayılmaz
    monkeypatch.setattr("builtins.input", lambda *_: "t")
    assert approval.request_approval(
        "skill", "sudo", "x", allow_session=False
    ) is False


def test_keyboard_interrupt_returns_false(monkeypatch):
    def raise_interrupt(*_):
        raise KeyboardInterrupt()

    monkeypatch.setattr("builtins.input", raise_interrupt)
    assert approval.request_approval("skill", "bash", "ls") is False
