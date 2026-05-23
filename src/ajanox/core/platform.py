"""Platform tespiti — merkezi OS algılama ve platforma özgü ipuçları.

Ajanox üç birinci-sınıf platform hedefler: macOS, Linux, WSL2 (Windows
üstünde Linux). Saf Windows (WSL'siz) desteklenmez — kullanıcı WSL2'ye
yönlendirilir.

Skill manifest'lerinde `requires.os: [linux, darwin, wsl]` ile platform
kısıtı belirtilir; `current_os()` katalog filtrelemede kullanılır.
"""

from __future__ import annotations

import functools
import platform as _platform
import sys
from pathlib import Path
from typing import Literal


Platform = Literal["macos", "linux", "wsl", "windows", "unknown"]


@functools.lru_cache(maxsize=1)
def is_wsl() -> bool:
    """WSL (Windows Subsystem for Linux) içinde mi çalışıyoruz?

    /proc/version içinde "microsoft" veya "WSL" geçer. WSL1 ve WSL2 ikisi de
    yakalanır.
    """
    if _platform.system() != "Linux":
        return False
    try:
        version = Path("/proc/version").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    lowered = version.lower()
    return "microsoft" in lowered or "wsl" in lowered


@functools.lru_cache(maxsize=1)
def current_os() -> Platform:
    """Geçerli platform — skill `requires.os` ile eşleşen kanonik ad."""
    system = _platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Linux":
        return "wsl" if is_wsl() else "linux"
    if system == "Windows":
        return "windows"
    return "unknown"


def os_aliases() -> frozenset[str]:
    """Geçerli platformun manifest'te eşleşebileceği tüm adlar.

    WSL hem "wsl" hem "linux" ile yazılmış skill'leri çalıştırabilir
    (WSL2 gerçek bir Linux kernel'i). macOS "darwin" alias'ını da kabul eder.
    """
    cur = current_os()
    if cur == "wsl":
        return frozenset({"wsl", "linux"})
    if cur == "macos":
        return frozenset({"macos", "darwin"})
    if cur == "linux":
        return frozenset({"linux"})
    if cur == "windows":
        return frozenset({"windows"})
    return frozenset({"unknown"})


def supports_skill_os(required_os: list[str] | None) -> bool:
    """Skill'in `requires.os` listesi geçerli platformla uyumlu mu?

    None / boş liste → her platformu destekler (kısıt yok).
    """
    if not required_os:
        return True
    declared = {str(o).strip().lower() for o in required_os}
    return bool(declared & os_aliases())


def ollama_host_hint() -> str:
    """Platforma özgü Ollama erişim ipucu (health check hatalarında)."""
    if current_os() == "wsl":
        return (
            "  WSL2 notu: Ollama'yı Windows host'ta çalıştırıyorsan, WSL içinden\n"
            "  localhost:11434 son WSL sürümlerinde forward edilir. Erişemiyorsan:\n"
            "    - Ollama'yı doğrudan WSL içinde kur (curl -fsSL https://ollama.ai/install.sh | sh), VEYA\n"
            "    - AJANOX_OLLAMA_URL=http://$(hostname).local:11434/api/chat ile host IP'sini ver"
        )
    return ""


def describe() -> str:
    """İnsan-okunur platform özeti (CLI başlığı / debug için)."""
    cur = current_os()
    labels = {
        "macos": "macOS",
        "linux": "Linux",
        "wsl": "WSL2 (Windows)",
        "windows": "Windows (WSL2 önerilir)",
        "unknown": "bilinmeyen platform",
    }
    return labels.get(cur, cur)
