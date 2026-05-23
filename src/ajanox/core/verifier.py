"""Tool-call verification — halüsinasyon koruma katmanı.

Agent loop bitince final cevabı, o turda gerçekten çağrılan tool'ların
trace'ine karşı kontrol eder. Üç sınıf halüsinasyonu yakalar:

1. **Unsupported claim** — "X dosyayı sildim" der ama bu turda silme
   tool'u çağrılmadı.
2. **Result mismatch** — bash hata döndü ama model "başarılı/tamam" der.
3. **Fabricated output** — final cevapta bash code bloğu/çıktısı var
   ama bash tool'u hiç çağrılmadı.

Heuristic — regex + trace cross-check. LLM-judge yok (pahalı,
non-deterministic, v0.7'ye bırakıldı).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Literal


Verdict = Literal["ok", "suspicious", "failed"]
Mode = Literal["warn", "strict", "off"]
WarningCode = Literal["unsupported_claim", "result_mismatch", "fabricated_output"]


@dataclass
class ToolTrace:
    """Bir tool çağrısının özeti — verifier için."""

    name: str
    args: dict
    success: bool
    output_preview: str  # ilk 500 karakter


@dataclass
class VerificationWarning:
    code: WarningCode
    claim: str           # bulduğumuz kelime/parça
    detail: str          # niçin uydurma sanıyoruz


@dataclass
class VerificationResult:
    verdict: Verdict
    warnings: list[VerificationWarning] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.verdict == "ok"


# --- Action verb patterns (TR past-tense) ---
#
# Her pattern model'in "yaptım/oldu/edildi" iddiasını yakalar.
# Yalnızca PAST tense — "sileceğim" (future), "silmen lazım" (imperative)
# yakalanmaz. Negative formlar ("silmedim") da yakalanmaz.
#
# Kelime sınırı `\b` Türkçe ekleri yanlış yakalamayı önler:
#   "sildim" ✓  "sildiğin dosyalar" ✗  "silmedim" ✗
_ACTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "delete": re.compile(
        r"\b(?:sil(?:di|dim|indi|inmiş)|kaldır(?:dı|dım|ıldı))\b",
        re.IGNORECASE,
    ),
    "create": re.compile(
        r"\b(?:oluştur(?:du|dum|uldu)|yaz(?:dım|ıldı)|kaydet(?:tim|ildi))\b",
        re.IGNORECASE,
    ),
    "install": re.compile(
        r"\b(?:kur(?:du|dum|uldu)|yükle(?:di|dim|ndi))\b",
        re.IGNORECASE,
    ),
    "run": re.compile(
        r"\b(?:çalıştır(?:dı|dım|ıldı)|başlat(?:tı|tım|ıldı))\b",
        re.IGNORECASE,
    ),
    "stop": re.compile(
        r"\b(?:durdur(?:du|dum|uldu)|kapat(?:tı|tım|ıldı)|sonlandır(?:dı|dım|ıldı))\b",
        re.IGNORECASE,
    ),
    "read": re.compile(
        r"\b(?:oku(?:du|dum|ndu)|incele(?:di|dim|ndi))\b",
        re.IGNORECASE,
    ),
    "list": re.compile(
        r"\b(?:listele(?:di|dim|ndi))\b",
        re.IGNORECASE,
    ),
}

# --- Hangi tool/komut hangi action'ı destekler ---
#
# Action → list of (tool_name, args_matcher). Trace'te bu eşleşmelerden
# en az biri başarılı çalışmışsa action "supported" sayılır.
_BashMatcher = re.Pattern[str]

_ACTION_SUPPORT: dict[str, list[tuple[str, _BashMatcher | None]]] = {
    "delete": [
        ("bash", re.compile(r"\b(?:rm|unlink|rmdir)\b")),
    ],
    "create": [
        # `touch X`, `mkdir X`, `> X`, `>> X` (redirect = oluşturur)
        ("bash", re.compile(r"\b(?:touch|mkdir|cp|mv)\b|>{1,2}\s*\S")),
    ],
    "install": [
        ("bash", re.compile(r"\b(?:apt|apt-get|brew|pip|pip3|npm|cargo)\s+install\b")),
    ],
    "run": [
        # Her başarılı bash çalıştığı sayılır
        ("bash", None),
    ],
    "stop": [
        ("bash", re.compile(r"\b(?:kill|pkill|killall)\b|\bsystemctl\s+stop\b")),
    ],
    "read": [
        ("read_file", None),
        ("bash", re.compile(r"\b(?:cat|head|tail|less|more)\b")),
    ],
    "list": [
        ("list_files", None),
        ("bash", re.compile(r"\b(?:ls|find|tree)\b")),
    ],
}

# Bash çıktısının "başarı" iddiası yansıttığı kalıplar.
_SUCCESS_CLAIM = re.compile(
    r"\b(?:başarılı|tamamland|tamam(?:dır)?|sorunsuz|hatasız|"
    r"başarıyla|başardım|halloldu|oldu\b)\b",
    re.IGNORECASE,
)

# Code-block / bash output kalıpları — fabricated output detection için.
_CODE_BLOCK = re.compile(r"```(?:bash|sh|shell)?\s*\n", re.IGNORECASE)


def _action_was_performed(action: str, trace: list[ToolTrace]) -> bool:
    """Trace'de bu action'ı destekleyen *başarılı* bir tool çağrısı var mı?"""
    matchers = _ACTION_SUPPORT.get(action, [])
    for entry in trace:
        if not entry.success:
            continue
        for tool_name, args_re in matchers:
            if entry.name != tool_name:
                continue
            if args_re is None:
                return True
            # bash için: command argümanına regex uygula
            command = str(entry.args.get("command", ""))
            if args_re.search(command):
                return True
    return False


def _bash_failed(entry: ToolTrace) -> bool:
    """Bir bash çağrısı hatayla mı bitti?"""
    if entry.name != "bash":
        return False
    if not entry.success:
        return True
    # primitives.bash() exit-nonzero'da "(exit N, no output)" döner
    if re.match(r"^\(exit [1-9]\d*,", entry.output_preview):
        return True
    return False


def verify(
    final_response: str,
    trace: list[ToolTrace],
    mode: Mode = "warn",
) -> VerificationResult:
    """Final cevabı trace'e karşı kontrol et.

    Args:
        final_response: model'in son düz-metin cevabı (tool-call etiketleri
            zaten temizlenmiş).
        trace: bu turda çağrılan tool'ların kayıt listesi.
        mode: 'off' → boş ok, 'warn'/'strict' → uyarı topla.

    Returns:
        VerificationResult — verdict + warning listesi.
    """
    if mode == "off" or not final_response.strip():
        return VerificationResult(verdict="ok")

    warnings: list[VerificationWarning] = []

    # 1) Unsupported action claims
    seen_actions: set[str] = set()  # her action'ı bir kez raporla
    for action, pattern in _ACTION_PATTERNS.items():
        match = pattern.search(final_response)
        if not match or action in seen_actions:
            continue
        if _action_was_performed(action, trace):
            continue
        seen_actions.add(action)
        warnings.append(
            VerificationWarning(
                code="unsupported_claim",
                claim=match.group(0),
                detail=(
                    f"Cevapta '{action}' eylem iddiası ('{match.group(0)}') var "
                    f"ama bu turda bunu destekleyen başarılı tool call yok."
                ),
            )
        )

    # 2) Result mismatch — bash error + model "başarılı" der
    failed_bash = [e for e in trace if _bash_failed(e)]
    if failed_bash and _SUCCESS_CLAIM.search(final_response):
        worst = failed_bash[-1]  # en son hata
        warnings.append(
            VerificationWarning(
                code="result_mismatch",
                claim="başarı iddiası",
                detail=(
                    f"Cevap başarı iddia ediyor ama son bash çağrısı "
                    f"hata döndü: {worst.output_preview[:120].strip()}"
                ),
            )
        )

    # 3) Fabricated output — bash code block + bash trace yok
    has_bash_trace = any(e.name == "bash" for e in trace)
    if not has_bash_trace and _CODE_BLOCK.search(final_response):
        warnings.append(
            VerificationWarning(
                code="fabricated_output",
                claim="bash code bloğu",
                detail=(
                    "Final cevapta bash/shell code bloğu var ama bu turda "
                    "hiç bash tool çağrılmadı — çıktı uydurma olabilir."
                ),
            )
        )

    if not warnings:
        verdict: Verdict = "ok"
    elif mode == "strict":
        verdict = "failed"
    else:
        verdict = "suspicious"

    return VerificationResult(verdict=verdict, warnings=warnings)


def get_mode() -> Mode:
    """AJANOX_VERIFY env değişkeninden mod oku. Default: 'warn'."""
    raw = (os.environ.get("AJANOX_VERIFY") or "warn").strip().lower()
    if raw in ("warn", "strict", "off"):
        return raw  # type: ignore[return-value]
    return "warn"


def format_warning_text(result: VerificationResult) -> str:
    """CLI/log için insan-okunur uyarı bloğu."""
    if result.ok:
        return ""
    icon = "✗" if result.verdict == "failed" else "⚠"
    lines = [f"{icon} Doğrulama ({result.verdict}):"]
    for w in result.warnings:
        lines.append(f"  - [{w.code}] {w.detail}")
    return "\n".join(lines)
