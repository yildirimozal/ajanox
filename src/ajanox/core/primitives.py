"""Temel primitives — her zaman yüklenen, skill'lerin üzerine inşa olduğu temel araçlar."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

BASH_TIMEOUT = 30
MAX_OUTPUT = 4000


def read_file(path: str) -> str:
    """Bir dosyayı UTF-8 olarak oku ve içeriğini döndür."""
    try:
        text = Path(os.path.expanduser(path)).read_text(encoding="utf-8")
        return text[:MAX_OUTPUT]
    except Exception as exc:
        return f"Hata: {exc}"


def list_files(directory: str) -> str:
    """Bir klasörün içeriğini listele."""
    try:
        items = os.listdir(os.path.expanduser(directory))
        return "\n".join(sorted(items)) if items else "(boş klasör)"
    except Exception as exc:
        return f"Hata: {exc}"


def bash(command: str) -> str:
    """Shell komutu çalıştır.

    UYARI: Bu primitive `shell_unsafe` permission'ı ister — yüksek riskli,
    her çağrıda runtime onayı gerekir. Skill'ler bunu doğrudan değil,
    permission katmanı üzerinden çağırmalıdır.
    """
    print(f"  [bash] $ {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=BASH_TIMEOUT,
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            output = f"(exit {result.returncode}, no output)"
        return output[:MAX_OUTPUT]
    except subprocess.TimeoutExpired:
        return f"Hata: {BASH_TIMEOUT} saniye içinde tamamlanmadı."
    except Exception as exc:
        return f"Hata: {exc}"


PRIMITIVES = {
    "read_file": read_file,
    "list_files": list_files,
    "bash": bash,
}
