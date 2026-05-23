"""Domain allowlist — skill'in network erişimini userspace'te kısıtla.

Skill manifest'i `network.allowed_domains` belirtirse, o skill'in bash
komutları yalnızca o domain'lere (ve alt-domain'lerine) erişebilir.
Listede olmayan bir hedef tespit edilirse komut çalıştırılmadan reddedilir.

Bu **userspace** (heuristic) bir savunma — komutu çalıştırmadan önce ağ
hedeflerini parse eder. Kararlı bir saldırgan obfuscation ile atlatabilir;
kernel-seviyesi (eBPF XDP) zorlama v3.0 hedefi. Yine de yaygın exfil
vektörlerini (curl/wget düz URL) kapatır.

Politika:
- `network_*` izni VAR + `allowed_domains` YOK → tüm domain'lere izin (geriye
  uyumlu; sandbox network namespace zaten açık).
- `network_*` izni VAR + `allowed_domains` set → SADECE o domain'ler.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass


# Argümanı ağ hedefi olan yaygın araçlar.
_NET_TOOLS: frozenset[str] = frozenset({
    "curl", "wget", "nc", "ncat", "netcat", "telnet", "ssh", "scp", "sftp",
    "ftp", "host", "dig", "nslookup", "ping", "ping6", "rsync", "aria2c",
    "http", "https", "httpie", "yt-dlp", "youtube-dl", "wscat", "mosh",
})

# Shell operatörleri — host-bekleme durumunu sıfırlar.
_SHELL_OPS: frozenset[str] = frozenset({"|", "||", "&&", ";", "&", ">", ">>", "<"})

_URL_RE = re.compile(r'https?://([^/\s:\'"]+)', re.IGNORECASE)

# Domain-benzeri token: en az bir nokta, geçerli label'lar, sonu TLD.
# "file.txt", "README.md" gibi şeyleri de yakalar — bu yüzden SADECE ağ
# aracı argümanı bağlamında kullanılır (düz dosya adlarını ağ hedefi sanmamak).
_DOMAIN_TOKEN = re.compile(
    r'^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$',
    re.IGNORECASE,
)


@dataclass
class DomainCheck:
    ok: bool
    targets: set[str]              # komutta bulunan tüm ağ hedefleri
    violations: set[str]           # allowlist dışı olanlar


def _clean_host(token: str) -> str:
    """Bir token'dan host kısmını çıkar: scheme, user@, path, port at."""
    host = re.sub(r'^[a-z][a-z0-9+.-]*://', '', token, flags=re.IGNORECASE)
    host = host.split('/')[0]       # path at
    host = host.split('@')[-1]      # user@host → host
    host = host.split('?')[0]
    host = host.rsplit(':', 1)[0] if host.count(':') == 1 else host  # port at
    return host.strip().lower()


def extract_network_targets(command: str) -> set[str]:
    """Komuttan ağ hedef domain'lerini çıkar.

    İki kaynak:
      1. http(s):// şemalı URL'ler (komutun herhangi bir yerinde)
      2. Bilinen ağ araçlarına (curl, wget, ssh...) verilen host argümanları
    """
    targets: set[str] = set()

    # 1) Şemalı URL'ler
    for m in _URL_RE.finditer(command):
        host = _clean_host(m.group(0))
        if host:
            targets.add(host)

    # 2) Ağ aracı argümanları
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    expect_host = False
    for tok in tokens:
        if tok in _SHELL_OPS:
            expect_host = False
            continue
        base = os.path.basename(tok)
        if base in _NET_TOOLS:
            expect_host = True
            continue
        if expect_host:
            if tok.startswith("-"):
                continue  # flag — host'u henüz bekliyoruz
            host = _clean_host(tok)
            if _DOMAIN_TOKEN.match(host):
                targets.add(host)
            # Flag olmayan ilk argümanı gördük; host beklemeyi bırak.
            expect_host = False

    return targets


def domain_allowed(domain: str, allowed: set[str]) -> bool:
    """domain, allowed listesinde mi? Exact veya alt-domain eşleşmesi.

    `example.com` → `example.com` ve `api.example.com` ✓; `notexample.com` ✗.
    """
    domain = domain.strip().lower()
    for a in allowed:
        a = a.strip().lower()
        if not a:
            continue
        if domain == a or domain.endswith("." + a):
            return True
    return False


def check_command(command: str, allowed_domains: set[str]) -> DomainCheck:
    """Komutun ağ hedefleri allowlist'e uyuyor mu?

    allowed_domains boşsa → kısıt yok (ok=True, herşeye izin).
    """
    if not allowed_domains:
        return DomainCheck(ok=True, targets=set(), violations=set())

    targets = extract_network_targets(command)
    violations = {t for t in targets if not domain_allowed(t, allowed_domains)}
    return DomainCheck(ok=not violations, targets=targets, violations=violations)
