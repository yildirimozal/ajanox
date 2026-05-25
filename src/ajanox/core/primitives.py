"""Temel primitives — her zaman yüklenen, skill'lerin üzerine inşa olduğu temel araçlar."""

from __future__ import annotations

import contextvars
import os
import subprocess
from pathlib import Path
from typing import Callable

from . import sandbox

BASH_TIMEOUT = 30
MAX_OUTPUT = 4000

# Agent loop, her tool çağrısından önce aktif skill'in permission setini
# bu ContextVar'a yazar. bash() sandbox'lamak için okur. ContextVar
# thread-safe — web server worker thread'leri arasında izole.
ACTIVE_PERMISSIONS: contextvars.ContextVar[frozenset[str]] = contextvars.ContextVar(
    "ajanox_active_permissions", default=frozenset()
)


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

    v0.7+: Sandbox aktifse (bwrap Linux / sandbox-exec macOS) komut izole
    ortamda çalışır. Hassas dizinler (~/.ssh, ~/.aws, ~/.gnupg) maskelidir,
    network sadece `network_*` permission'ı varsa açılır.
    """
    print(f"  [bash] $ {command}")
    plan = sandbox.plan(command, ACTIVE_PERMISSIONS.get())

    if plan.blocked:
        return f"Hata: sandbox bloğu — {plan.warning}"
    if plan.warning:
        print(f"  [sandbox] uyarı: {plan.warning}")

    profile_path: str | None = None
    try:
        if plan.backend == "none":
            # Sandbox yok — eski davranış (shell=True)
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=BASH_TIMEOUT,
            )
        else:
            argv, profile_path = sandbox.materialize(plan)
            result = subprocess.run(
                argv,
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
    finally:
        if profile_path:
            try:
                os.unlink(profile_path)
            except OSError:
                pass


PRIMITIVES: dict[str, Callable[..., str]] = {
    "read_file": read_file,
    "list_files": list_files,
    "bash": bash,
}
