"""Ajanox CLI entry point.

Kullanım:
  ajanox                 — doğal dil shell başlatır (varsayılan)
  ajanox shell           — aynı, açık
  ajanox skill init NAME — yeni skill boilerplate üret
  ajanox skill list      — yüklü skill'leri listele
  ajanox skill check     — skill'in spec'e uyumunu kontrol et
"""

from __future__ import annotations

import sys

from . import shell, skill


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] == "shell":
        return shell.run()
    if argv[0] == "skill":
        return skill.run(argv[1:])
    print(f"Bilinmeyen komut: {argv[0]}", file=sys.stderr)
    print(__doc__, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
