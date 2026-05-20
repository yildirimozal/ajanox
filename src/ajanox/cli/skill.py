"""`ajanox skill` subcommand'leri.

STATUS: stub. İleride doldurulacak — şimdilik signature + plan.
"""

from __future__ import annotations

import sys


USAGE = """
Kullanım: ajanox skill <komut> [args]

Komutlar:
  init <name>     Yeni skill için boilerplate üret (spec v0.1 manifest ile)
  list            Yüklü skill'leri listele
  check <path>    Bir SKILL.md'nin spec'e uyumunu kontrol et
  migrate <path>  v0.x manifest'i v1.0 formatına yükselt (henüz yok)
"""


def run(args: list[str]) -> int:
    if not args:
        print(USAGE, file=sys.stderr)
        return 1

    cmd = args[0]
    rest = args[1:]

    if cmd == "init":
        return _init(rest)
    if cmd == "list":
        return _list()
    if cmd == "check":
        return _check(rest)
    if cmd == "migrate":
        return _migrate(rest)

    print(f"Bilinmeyen skill komutu: {cmd}", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return 1


def _init(args: list[str]) -> int:
    if not args:
        print("Kullanım: ajanox skill init <name>", file=sys.stderr)
        return 1
    print(f"(TODO) Skill boilerplate oluşturulacak: {args[0]}")
    return 0


def _list() -> int:
    print("(TODO) Yüklü skill'ler listelenecek")
    return 0


def _check(args: list[str]) -> int:
    if not args:
        print("Kullanım: ajanox skill check <path>", file=sys.stderr)
        return 1
    print(f"(TODO) Spec uyumluluğu kontrol edilecek: {args[0]}")
    return 0


def _migrate(args: list[str]) -> int:
    print("(TODO) v1.0 yayınlandığında implement edilecek")
    return 0
