"""Tool-call verifier testleri."""

from __future__ import annotations

import pytest

from ajanox.core.verifier import (
    ToolTrace,
    VerificationResult,
    format_warning_text,
    get_mode,
    verify,
)


def _bash(command: str, output: str = "", success: bool = True) -> ToolTrace:
    return ToolTrace(
        name="bash",
        args={"command": command},
        success=success,
        output_preview=output,
    )


def _read(path: str = "/tmp/x", output: str = "ok", success: bool = True) -> ToolTrace:
    return ToolTrace(
        name="read_file",
        args={"path": path},
        success=success,
        output_preview=output,
    )


# --- mode handling ---

def test_off_mode_returns_ok_without_inspection():
    result = verify("3 dosyayı sildim", trace=[], mode="off")
    assert result.verdict == "ok"
    assert result.warnings == []


def test_empty_response_is_ok():
    result = verify("", trace=[], mode="warn")
    assert result.verdict == "ok"


def test_get_mode_default(monkeypatch):
    monkeypatch.delenv("AJANOX_VERIFY", raising=False)
    assert get_mode() == "warn"


def test_get_mode_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("AJANOX_VERIFY", "garbage")
    assert get_mode() == "warn"


@pytest.mark.parametrize("value", ["warn", "strict", "off"])
def test_get_mode_valid(monkeypatch, value):
    monkeypatch.setenv("AJANOX_VERIFY", value)
    assert get_mode() == value


# --- 1) Unsupported claim ---

def test_delete_claim_without_tool_is_flagged():
    result = verify("3 dosyayı sildim.", trace=[], mode="warn")
    assert result.verdict == "suspicious"
    assert len(result.warnings) == 1
    assert result.warnings[0].code == "unsupported_claim"


def test_delete_claim_with_rm_bash_is_ok():
    result = verify(
        "3 dosyayı sildim.",
        trace=[_bash("rm -f /tmp/a /tmp/b /tmp/c", "")],
        mode="warn",
    )
    assert result.ok


def test_install_claim_without_install_command_is_flagged():
    # `bash echo "ok"` install action'ını desteklemez
    result = verify(
        "Paket kuruldu.",
        trace=[_bash("echo done", "done")],
        mode="warn",
    )
    assert result.verdict == "suspicious"
    assert result.warnings[0].code == "unsupported_claim"


def test_install_claim_with_apt_install_is_ok():
    result = verify(
        "Paket kuruldu.",
        trace=[_bash("sudo apt install vim", "Reading package lists...")],
        mode="warn",
    )
    assert result.ok


def test_read_claim_with_read_file_tool_is_ok():
    result = verify(
        "Dosyayı okudum, içinde 3 satır var.",
        trace=[_read("/tmp/x", "line1\nline2\nline3")],
        mode="warn",
    )
    assert result.ok


def test_list_claim_with_ls_bash_is_ok():
    result = verify(
        "Klasörü listeledim.",
        trace=[_bash("ls /tmp", "a.txt\nb.txt")],
        mode="warn",
    )
    assert result.ok


def test_negated_past_tense_not_flagged():
    # "silmedim" — geçmişte yapmadığını söylüyor → uyarı çıkmamalı
    result = verify("Hiçbir şey silmedim.", trace=[], mode="warn")
    assert result.ok


def test_future_tense_not_flagged():
    result = verify("Yarın sileceğim.", trace=[], mode="warn")
    assert result.ok


def test_imperative_not_flagged():
    result = verify("Bu dosyayı silmen lazım.", trace=[], mode="warn")
    assert result.ok


def test_inside_word_not_flagged():
    # "sildiğin" — ek alır, past-tense iddia değil
    result = verify("Sildiğin dosyaları geri al.", trace=[], mode="warn")
    assert result.ok


def test_same_action_reported_once():
    # İki "sildim" geçse de tek warning üretilmeli
    result = verify("X'i sildim. Ayrıca Y'yi de sildim.", trace=[], mode="warn")
    assert len([w for w in result.warnings if w.code == "unsupported_claim"]) == 1


def test_failed_tool_does_not_count_as_supported():
    # bash rm çalıştı ama başarısız döndü (success=False) — claim hala unsupported
    result = verify(
        "Sildim.",
        trace=[_bash("rm /tmp/missing", "rm: cannot remove", success=False)],
        mode="warn",
    )
    assert result.verdict == "suspicious"
    assert any(w.code == "unsupported_claim" for w in result.warnings)


# --- 2) Result mismatch ---

def test_bash_exit_nonzero_with_success_claim_is_flagged():
    result = verify(
        "İşlem başarılı.",
        trace=[_bash("ls /no/such", "(exit 2, no output)")],
        mode="warn",
    )
    codes = [w.code for w in result.warnings]
    assert "result_mismatch" in codes


def test_bash_success_with_success_claim_is_ok():
    result = verify(
        "Tamam, başarılı.",
        trace=[_bash("ls /tmp", "a.txt")],
        mode="warn",
    )
    # "tamam" iddia ile ls success — mismatch yok (run action'ı destekleniyor)
    assert "result_mismatch" not in [w.code for w in result.warnings]


def test_bash_failure_without_success_claim_is_ok():
    result = verify(
        "Dosya zaten silinmiş görünüyor.",
        trace=[_bash("rm /tmp/missing", "(exit 1, no output)", success=False)],
        mode="warn",
    )
    assert "result_mismatch" not in [w.code for w in result.warnings]


# --- 3) Fabricated output ---

def test_code_block_without_bash_trace_is_flagged():
    result = verify(
        "Şu çıktıyı aldım:\n```bash\nls /tmp\nfile1.txt\nfile2.txt\n```",
        trace=[],
        mode="warn",
    )
    assert any(w.code == "fabricated_output" for w in result.warnings)


def test_code_block_with_bash_trace_is_ok():
    result = verify(
        "Klasörü listeledim:\n```bash\nls /tmp\n```",
        trace=[_bash("ls /tmp", "file1.txt")],
        mode="warn",
    )
    assert not any(w.code == "fabricated_output" for w in result.warnings)


def test_plain_text_code_block_not_flagged():
    # Code block ama dil belirtilmemiş bash değil → fabricated kontrolü yapmaz
    result = verify(
        "Şöyle yapabilirsin:\n```python\nprint('x')\n```",
        trace=[],
        mode="warn",
    )
    assert not any(w.code == "fabricated_output" for w in result.warnings)


# --- strict mode ---

def test_strict_mode_promotes_to_failed():
    result = verify("Sildim.", trace=[], mode="strict")
    assert result.verdict == "failed"


def test_strict_mode_ok_when_no_warnings():
    result = verify(
        "Sildim.",
        trace=[_bash("rm /tmp/x", "")],
        mode="strict",
    )
    assert result.verdict == "ok"


# --- format helper ---

def test_format_warning_text_empty_when_ok():
    assert format_warning_text(VerificationResult(verdict="ok")) == ""


def test_format_warning_text_includes_codes():
    result = verify("Sildim. Kurdum.", trace=[], mode="warn")
    text = format_warning_text(result)
    assert "Doğrulama" in text
    assert "unsupported_claim" in text
