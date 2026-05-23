"""Bash sandbox — bwrap (Linux) ve sandbox-exec (macOS) ile process izolasyonu.

Tek satır özet: bash komutu kullanıcı onayı alsa bile izole bir ortamda
çalışsın, izinli olmayan dosyalara/network'e ulaşamasın.

Permission → sandbox profili çevirisi:
  shell_safe / shell_unsafe          → temel jail
  + file_write                       → /tmp yazılabilir (default: ro)
  + network_read / network_write     → ağa erişim (default: kapalı)
  hassas dizinler (~/.ssh, ~/.aws,
  ~/.gnupg, ~/.config/git)           → her zaman maskeli

Modlar (AJANOX_SANDBOX env):
  auto   — backend varsa kullan, yoksa uyarı + sandbox'sız çalış (default)
  on     — backend yoksa bash'i çalıştırmayı reddet
  off    — sandbox tamamen kapalı

NOT: read_file / list_files şu an sandbox'a tabi değil (Python-internal,
sürecin kendi yetkisiyle okur). v0.8'de path-allowlist eklenecek.
"""

from __future__ import annotations

import os
import platform
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Iterable, Literal


Backend = Literal["bwrap", "sandbox-exec", "none"]
Mode = Literal["auto", "on", "off"]


# Her zaman maskelenen hassas ev dizini alt yolları
_SENSITIVE_HOME_SUBDIRS: tuple[str, ...] = (
    ".ssh",
    ".aws",
    ".gnupg",
    ".config/git",
    ".config/gh",       # GitHub CLI tokens
    ".docker/config.json",
    ".kube/config",
    ".netrc",
)


@dataclass
class SandboxPlan:
    """Bir bash çağrısı için seçilen sandbox stratejisi."""

    backend: Backend
    wrapped_argv: list[str] = field(default_factory=list)
    profile_text: str | None = None       # sandbox-exec için
    warning: str | None = None            # kullanıcıya gösterilecek not
    blocked: bool = False                 # mode=on + backend yok → True


def get_mode() -> Mode:
    raw = (os.environ.get("AJANOX_SANDBOX") or "auto").strip().lower()
    if raw in ("auto", "on", "off"):
        return raw  # type: ignore[return-value]
    return "auto"


def detect_backend() -> Backend:
    """Sistem üstünde hangi sandbox aracı kullanılabilir?"""
    system = platform.system()
    if system == "Linux":
        if shutil.which("bwrap"):
            return "bwrap"
    elif system == "Darwin":
        # sandbox-exec her macOS'ta var (deprecated ama hâlâ çalışıyor)
        if shutil.which("sandbox-exec"):
            return "sandbox-exec"
    return "none"


def _expand_home(*parts: str) -> str:
    return os.path.join(os.path.expanduser("~"), *parts)


def _normalize_perms(permissions: Iterable[str] | None) -> frozenset[str]:
    return frozenset(permissions or ())


# ---------- Linux: bwrap ----------

def build_bwrap_argv(command: str, permissions: Iterable[str] | None) -> list[str]:
    """bwrap çağrı argümanları — `command` jail içinde `bash -c` ile çalışır.

    Default: root filesystem read-only, /tmp tmpfs (yazılabilir ama izole),
    network kapalı, hassas ev dizinleri maskelenmiş.
    """
    perms = _normalize_perms(permissions)
    argv: list[str] = [
        "bwrap",
        # Tüm root'u read-only bağla
        "--ro-bind", "/", "/",
        # /dev /proc /tmp izole
        "--dev", "/dev",
        "--proc", "/proc",
        "--tmpfs", "/tmp",
        # Parent ölünce öl
        "--die-with-parent",
        # Namespace izolasyonu
        "--unshare-uts",
        "--unshare-ipc",
        "--unshare-cgroup-try",
    ]

    # Network: opt-in
    if "network_read" in perms or "network_write" in perms:
        argv.append("--share-net")
    else:
        argv.append("--unshare-net")

    # Hassas dizinleri tmpfs ile maskele. bwrap --tmpfs mount point'in var
    # olmasını ister (read-only root altında yeni dizin yaratılamaz), bu yüzden
    # yalnız var olan path'leri maskeliyoruz. Dosyaları /dev/null'a ro-bind'le.
    for rel in _SENSITIVE_HOME_SUBDIRS:
        path = _expand_home(rel)
        if not os.path.exists(path):
            continue
        if os.path.isdir(path):
            argv.extend(["--tmpfs", path])
        else:
            argv.extend(["--ro-bind", "/dev/null", path])

    # file_write izni varsa /tmp'i gerçek /tmp'e bağla (kalıcı yazım)
    # Yoksa zaten --tmpfs /tmp izole tmpfs'tir, jail süresince yazılır.
    # Default skill scratch için izole tmpfs yeterli.

    argv.extend(["--", "bash", "-c", command])
    return argv


# ---------- macOS: sandbox-exec ----------

def build_sandbox_exec_profile(permissions: Iterable[str] | None) -> str:
    """sandbox-exec için SBPL profili.

    Default: deny network + sensitive home dirs; allow file-read* + tmpfs benzeri
    /tmp yazımı; file_write izni eklerse /Users/<u>/Documents da yazılabilir
    yapılır (v0.7 first cut — sonra daha incelikli kuralllar).
    """
    perms = _normalize_perms(permissions)
    home = os.path.expanduser("~")

    profile = [
        "(version 1)",
        "(allow default)",
        # Default-deny olan iki şey: network + hassas dosyalar
        "(deny network*)",
        "(deny file-write*)",
        # Her zaman maskeli yollar
    ]
    for rel in _SENSITIVE_HOME_SUBDIRS:
        full = os.path.join(home, rel)
        profile.append(f'(deny file-read* (subpath "{full}"))')

    # /tmp yazımı: skill scratch
    profile.append('(allow file-write* (subpath "/tmp"))')
    profile.append('(allow file-write* (subpath "/private/tmp"))')

    if "file_write" in perms:
        # Kullanıcının Documents/Downloads alanlarını da yaz-izinli yap.
        # NOT: daha sıkı path allowlist v0.8'de gelecek.
        profile.append(f'(allow file-write* (subpath "{home}/Documents"))')
        profile.append(f'(allow file-write* (subpath "{home}/Downloads"))')
        profile.append('(allow file-write* (subpath "/var/folders"))')

    if "network_read" in perms or "network_write" in perms:
        profile.append("(allow network*)")

    return "\n".join(profile) + "\n"


def build_sandbox_exec_argv(
    command: str, permissions: Iterable[str] | None
) -> tuple[list[str], str]:
    """(argv, profile_text) döner — caller profile_text'i tmp dosyaya yazar."""
    profile = build_sandbox_exec_profile(permissions)
    # argv'de profile dosyasını -f ile veriyoruz; dosya caller'da oluşturulur
    return (
        ["sandbox-exec", "-f", "<PROFILE_PATH>", "bash", "-c", command],
        profile,
    )


# ---------- Plan oluşturma ----------

def plan(command: str, permissions: Iterable[str] | None) -> SandboxPlan:
    """Geçerli env + platform için bir SandboxPlan üret.

    Caller bu planı `apply_plan(...)` ile subprocess.run'a hazırlayabilir.
    """
    mode = get_mode()
    backend = detect_backend()

    if mode == "off":
        return SandboxPlan(backend="none")

    if backend == "none":
        # mode=on iken backend yoksa → blokla
        if mode == "on":
            return SandboxPlan(
                backend="none",
                blocked=True,
                warning=(
                    "AJANOX_SANDBOX=on ama bu sistemde sandbox backend yok "
                    "(Linux: bwrap, macOS: sandbox-exec gerekli). "
                    "Komut çalıştırılmadı."
                ),
            )
        return SandboxPlan(
            backend="none",
            warning=(
                "Sandbox backend yok (bwrap/sandbox-exec). "
                "Komut sandbox'sız çalışıyor — "
                "Linux'ta `apt install bubblewrap` öneriyoruz."
            ),
        )

    if backend == "bwrap":
        return SandboxPlan(
            backend="bwrap",
            wrapped_argv=build_bwrap_argv(command, permissions),
        )

    if backend == "sandbox-exec":
        argv, profile = build_sandbox_exec_argv(command, permissions)
        return SandboxPlan(
            backend="sandbox-exec",
            wrapped_argv=argv,
            profile_text=profile,
        )

    return SandboxPlan(backend="none")


def materialize(plan_: SandboxPlan) -> tuple[list[str], str | None]:
    """Plan'ı subprocess.run'a hazır argv'ye çevir.

    sandbox-exec için profile dosyasını disk'e yazar ve argv'deki
    `<PROFILE_PATH>` placeholder'ını gerçek yolla değiştirir.

    Returns: (argv, tmp_profile_path or None) — tmp varsa caller sonradan
    siler (best-effort; OS tmpdir reaper de halleder).
    """
    if plan_.backend == "sandbox-exec" and plan_.profile_text:
        fd, tmp_path = tempfile.mkstemp(prefix="ajanox-sbx-", suffix=".sb")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(plan_.profile_text)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise
        argv = [
            tmp_path if a == "<PROFILE_PATH>" else a for a in plan_.wrapped_argv
        ]
        return argv, tmp_path
    return plan_.wrapped_argv, None
