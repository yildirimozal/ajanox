"""`ajanox web` — web dashboard'u başlat."""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser


def run(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="ajanox web",
        description="Ajanox web dashboard'u başlat",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind edilecek host (default: 127.0.0.1 — yalnız localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port (default: 8765)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Tarayıcıyı otomatik açma",
    )
    ns = parser.parse_args(args)

    try:
        from ..web.server import start_server
    except ImportError as exc:
        print(
            "✗ Web dashboard için ek bağımlılıklar gerekli.\n"
            "  Kurulum: pip install 'ajanox[web]'",
            file=sys.stderr,
        )
        print(f"  ({exc})", file=sys.stderr)
        return 1

    # Ön gereksinim kontrolü — Ollama + model
    from ..core.agent import DEFAULT_MODEL, check_ollama_health
    model = os.environ.get("AJANOX_MODEL", DEFAULT_MODEL)
    ok, health_msg = check_ollama_health(model)
    print(health_msg)
    if not ok:
        print(
            "\n⚠️  Web dashboard başlatılmadı. Ollama + model hazır olduktan\n"
            "    sonra `ajanox web` komutunu tekrar çalıştır.",
            file=sys.stderr,
        )
        return 1

    url = f"http://{ns.host}:{ns.port}"
    print(f"\nAjanox web dashboard başlatılıyor: {url}")
    print(f"Model: {model}")
    print()

    if not ns.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        start_server(host=ns.host, port=ns.port)
    except KeyboardInterrupt:
        print("\nKapatılıyor.")
    return 0
