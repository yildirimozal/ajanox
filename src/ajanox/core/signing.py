"""Skill imzalama — ed25519 + TOFU güven modeli.

Yazar SKILL.md'yi özel anahtarıyla imzalar; kullanıcı kurarken doğrular.
Marketplace'te "ismen güven" yerine "kodla güven" sağlar.

Mimari:
- İmza ed25519 (cryptography kütüphanesi — opsiyonel `ajanox[signing]` extra).
- İmza, SKILL.md'nin TAM byte'ları üzerinden hesaplanır (detached).
- Detached imza dosyası: `SKILL.md.sig` — pubkey + signature (hex) içerir.
- Güven: TOFU (trust-on-first-use). İlk kurulumda yazar pubkey'i
  `~/.ajanox/trust/<skill>.pub`'a kaydedilir; sonraki güncellemede anahtar
  değişirse yüksek sesle uyarılır (SSH known_hosts modeli).

cryptography kurulu değilse keygen/sign/verify net bir hata verir; temel
CLI çalışmaya devam eder (signing opsiyonel extra).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


TRUST_DIR = Path(os.environ.get("AJANOX_HOME", str(Path.home() / ".ajanox"))) / "trust"

TrustState = Literal["new", "match", "changed"]


class SigningUnavailable(RuntimeError):
    """cryptography kurulu değil."""


@dataclass
class VerifyResult:
    valid: bool                      # imza matematiksel olarak geçerli mi
    trust: TrustState                # TOFU durumu
    pubkey: str                      # imzalayan pubkey (hex)
    previous_pubkey: str | None = None  # trust=changed ise eski anahtar
    error: str | None = None


def _require_crypto():
    """cryptography'yi lazy import et; yoksa net hata."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: F401

        return ed25519
    except ImportError as exc:  # pragma: no cover
        raise SigningUnavailable(
            "Skill imzalama için 'cryptography' gerekli.\n"
            "  Kurulum: pip install 'ajanox[signing]'  (veya: pip install cryptography)"
        ) from exc


# ---------- Anahtar üretimi ----------

def generate_keypair() -> tuple[str, str]:
    """Yeni ed25519 anahtar çifti üret. (private_hex, public_hex) döner."""
    ed25519 = _require_crypto()
    from cryptography.hazmat.primitives import serialization

    priv = ed25519.Ed25519PrivateKey.generate()
    raw_priv = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    raw_pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw_priv.hex(), raw_pub.hex()


def public_from_private(private_hex: str) -> str:
    """Özel anahtardan public anahtarı türet (hex)."""
    ed25519 = _require_crypto()
    from cryptography.hazmat.primitives import serialization

    priv = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_hex.strip()))
    return priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


# ---------- İmzalama ----------

def _sig_path(skill_md: Path) -> Path:
    return skill_md.with_name(skill_md.name + ".sig")


def sign_file(skill_md: Path, private_hex: str) -> Path:
    """SKILL.md'yi imzala, `SKILL.md.sig` yaz. Sig dosya yolunu döner."""
    ed25519 = _require_crypto()

    priv = ed25519.Ed25519PrivateKey.from_private_bytes(
        bytes.fromhex(private_hex.strip())
    )
    message = skill_md.read_bytes()
    signature = priv.sign(message)
    pubkey_hex = public_from_private(private_hex)

    sig_path = _sig_path(skill_md)
    sig_path.write_text(
        "# Ajanox skill signature (ed25519)\n"
        f"pubkey: {pubkey_hex}\n"
        f"signature: {signature.hex()}\n",
        encoding="utf-8",
    )
    return sig_path


def _parse_sig(sig_path: Path) -> tuple[str, str]:
    """(pubkey_hex, signature_hex) — eksikse ValueError."""
    pubkey = sig = ""
    for line in sig_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("pubkey:"):
            pubkey = line.split(":", 1)[1].strip()
        elif line.startswith("signature:"):
            sig = line.split(":", 1)[1].strip()
    if not pubkey or not sig:
        raise ValueError("sig dosyası eksik (pubkey/signature yok)")
    return pubkey, sig


# ---------- TOFU güven deposu ----------

def _trust_file(skill_name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in skill_name)
    return TRUST_DIR / f"{safe}.pub"


def trust_state(skill_name: str, pubkey_hex: str) -> tuple[TrustState, str | None]:
    """Bu pubkey daha önce bu skill için görüldü mü? (state, previous_pubkey)."""
    tf = _trust_file(skill_name)
    if not tf.exists():
        return "new", None
    stored = tf.read_text(encoding="utf-8").strip()
    if stored == pubkey_hex.strip():
        return "match", stored
    return "changed", stored


def record_trust(skill_name: str, pubkey_hex: str) -> None:
    """Pubkey'i bu skill için TOFU deposuna yaz (üzerine yazar)."""
    TRUST_DIR.mkdir(parents=True, exist_ok=True)
    _trust_file(skill_name).write_text(pubkey_hex.strip() + "\n", encoding="utf-8")


# ---------- Doğrulama ----------

def verify_file(
    skill_md: Path,
    skill_name: str,
    record_on_new: bool = True,
) -> VerifyResult:
    """SKILL.md imzasını doğrula + TOFU kontrolü.

    Args:
        skill_md: SKILL.md yolu (yanında SKILL.md.sig olmalı)
        skill_name: TOFU deposunda anahtar adı
        record_on_new: ilk görülen pubkey'i otomatik kaydet (TOFU)

    Returns:
        VerifyResult — valid (kripto), trust (TOFU durumu), pubkey.
    """
    ed25519 = _require_crypto()

    sig_path = _sig_path(skill_md)
    if not sig_path.exists():
        return VerifyResult(valid=False, trust="new", pubkey="", error="imza dosyası yok (SKILL.md.sig)")

    try:
        pubkey_hex, signature_hex = _parse_sig(sig_path)
    except ValueError as exc:
        return VerifyResult(valid=False, trust="new", pubkey="", error=str(exc))

    message = skill_md.read_bytes()
    try:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pubkey_hex))
        pub.verify(bytes.fromhex(signature_hex), message)
        valid = True
    except Exception as exc:  # InvalidSignature dahil
        return VerifyResult(
            valid=False, trust="new", pubkey=pubkey_hex,
            error=f"imza geçersiz: {type(exc).__name__}",
        )

    state, previous = trust_state(skill_name, pubkey_hex)
    if state == "new" and record_on_new:
        record_trust(skill_name, pubkey_hex)

    return VerifyResult(
        valid=valid, trust=state, pubkey=pubkey_hex, previous_pubkey=previous
    )
