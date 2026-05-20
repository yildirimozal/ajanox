"""Ajanox Web Dashboard — FastAPI server + WebSocket protokolü.

Mesaj protokolü (WebSocket /ws):

Client → Server:
  {"type": "user_message", "content": "..."}
  {"type": "reset"}

Server → Client (event stream):
  {"type": "match", "skill": "weather", "score": 3}
  {"type": "tool_call", "tool": "bash", "args": {...}}
  {"type": "tool_result", "tool": "bash", "output": "..."}
  {"type": "denied", "tool": "...", "skill": "..."}
  {"type": "final", "content": "İstanbul'da hava güneşli..."}
  {"type": "done"}  # turn bitti
  {"type": "error", "message": "..."}
"""

from __future__ import annotations

import asyncio
import os
import queue
import threading
from pathlib import Path

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Ajanox web dashboard için FastAPI ve uvicorn gerekli. "
        "Kurulum: pip install ajanox[web]"
    ) from exc

from ..cli.shell import _collect_skills
from ..core.agent import DEFAULT_MODEL, run_agent
from .. import __version__


STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Ajanox Web Dashboard", version=__version__)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/info")
async def info() -> dict:
    catalog, sources = _collect_skills()
    return {
        "version": __version__,
        "model": os.environ.get("AJANOX_MODEL", DEFAULT_MODEL),
        "skills": [
            {
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "permissions": list(s.permissions),
            }
            for s in catalog
        ],
        "sources": sources,
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    catalog, _ = _collect_skills()
    model = os.environ.get("AJANOX_MODEL", DEFAULT_MODEL)
    history: list[dict] = []

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "reset":
                history = []
                await ws.send_json({"type": "reset_ok"})
                continue

            if msg_type != "user_message":
                await ws.send_json(
                    {"type": "error", "message": f"Bilinmeyen mesaj tipi: {msg_type}"}
                )
                continue

            user_input = (data.get("content") or "").strip()
            if not user_input:
                continue

            # Agent loop'unu thread'de çalıştır + event'leri queue üzerinden stream et
            event_q: queue.Queue = queue.Queue()

            def on_event(event: dict) -> None:
                event_q.put(event)

            def runner() -> None:
                nonlocal history
                try:
                    history = run_agent(
                        user_input,
                        catalog,
                        history=history,
                        model=model,
                        on_event=on_event,
                    )
                except Exception as exc:  # noqa: BLE001
                    event_q.put({"type": "error", "message": str(exc)})
                finally:
                    event_q.put({"type": "done"})

            thread = threading.Thread(target=runner, daemon=True)
            thread.start()

            # Queue'dan event'leri al, WebSocket'a yolla
            loop = asyncio.get_event_loop()
            while True:
                event = await loop.run_in_executor(None, event_q.get)
                await ws.send_json(event)
                if event.get("type") == "done":
                    break
    except WebSocketDisconnect:
        pass


def start_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Sunucuyu başlat. Production: prod-grade WSGI değil, geliştirme modu."""
    uvicorn.run(app, host=host, port=port, log_level="info")
