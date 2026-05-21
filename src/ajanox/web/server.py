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
import urllib.error
import uuid
from pathlib import Path

try:
    from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Ajanox web dashboard için FastAPI ve uvicorn gerekli. "
        "Kurulum: pip install ajanox[web]"
    ) from exc

from ..cli.shell import _collect_skills
from ..core import approval, registry as reg_mod
from ..core.agent import DEFAULT_MODEL, run_agent
from ..core.permissions import PERMISSION_RISK, validate_permissions
from ..core.skill_loader import parse_frontmatter
from .. import __version__


APPROVAL_TIMEOUT_SECONDS = 120


STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Ajanox Web Dashboard", version=__version__)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/info")
async def info() -> dict:
    catalog, sources = _collect_skills()
    # Dedup: aynı skill name birden fazla kaynaktan gelirse (örn. builtin +
    # cwd/skills) ilk gördüğümüzü tut. Kullanıcı panelde duplikat görmesin.
    seen: set[str] = set()
    unique = []
    for s in catalog:
        if s.name in seen:
            continue
        seen.add(s.name)
        unique.append(s)
    return {
        "version": __version__,
        "model": os.environ.get("AJANOX_MODEL", DEFAULT_MODEL),
        "skills": [
            {
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "permissions": list(s.permissions),
                "icon": s.icon,
                "example_prompt": s.example_prompt,
            }
            for s in unique
        ],
        "sources": sources,
    }


class WebApprovalBroker:
    """Async event loop ↔ sync agent thread arası approval köprüsü.

    Agent (sync, thread'de) `request()` çağırır → modal event'i WebSocket'a
    yollar (async) → kullanıcı tıklar → `resolve()` (async, WS handler'dan) →
    threading.Event set olur → agent thread bekleme biter, kararı döner.
    """

    def __init__(self, ws: WebSocket, loop: asyncio.AbstractEventLoop) -> None:
        self.ws = ws
        self.loop = loop
        self._pending: dict[str, threading.Event] = {}
        self._responses: dict[str, str] = {}

    def request(
        self, skill: str, tool: str, command: str, risk: str, allow_session: bool
    ) -> str:
        """Agent thread'den çağrılır. WS'e event yollar, response bekler."""
        req_id = str(uuid.uuid4())
        event = threading.Event()
        self._pending[req_id] = event

        payload = {
            "type": "approval_request",
            "request_id": req_id,
            "skill": skill,
            "tool": tool,
            "command": command,
            "risk": risk,
            "allow_session": allow_session,
        }
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws.send_json(payload), self.loop
            ).result(timeout=5)
        except Exception:
            self._pending.pop(req_id, None)
            return "no"

        if not event.wait(timeout=APPROVAL_TIMEOUT_SECONDS):
            self._pending.pop(req_id, None)
            return "no"
        return self._responses.pop(req_id, "no")

    def resolve(self, request_id: str, decision: str) -> bool:
        """WS handler'dan çağrılır. response'u kayıtla + event'i set et."""
        if request_id not in self._pending:
            return False
        self._responses[request_id] = decision
        self._pending.pop(request_id).set()
        return True


# ─────────────────────────────────────────────────────────────────────
# Marketplace HTTP endpoints
# ─────────────────────────────────────────────────────────────────────

# Cache: registry skill listeleri (GitHub API call'larını azaltmak için)
_marketplace_cache: dict = {"skills": None, "ts": 0.0}
_MARKETPLACE_CACHE_TTL = 300  # 5 dakika


def _user_installed_names() -> set[str]:
    """~/.ajanox/skills/ altında yüklü kullanıcı skill isimleri."""
    home = Path(os.environ.get("AJANOX_HOME", str(Path.home() / ".ajanox")))
    skills_dir = home / "skills"
    if not skills_dir.exists():
        return set()
    return {p.name for p in skills_dir.iterdir() if (p / "SKILL.md").exists()}


@app.get("/api/marketplace/skills")
async def marketplace_skills(refresh: bool = False) -> dict:
    """Tüm kayıtlı registry'lerdeki skill isimlerini listele (cache'li)."""
    import time
    now = time.time()
    if (
        not refresh
        and _marketplace_cache["skills"]
        and (now - _marketplace_cache["ts"]) < _MARKETPLACE_CACHE_TTL
    ):
        installed = _user_installed_names()
        for s in _marketplace_cache["skills"]:
            s["installed"] = s["name"] in installed
        return {"skills": _marketplace_cache["skills"]}

    registries = reg_mod.load_registries()
    installed = _user_installed_names()
    out: list[dict] = []
    for r in registries:
        try:
            names = reg_mod.list_registry_skills(r)
        except ValueError:
            continue
        for name in names:
            out.append({
                "name": name,
                "registry": r.name,
                "registry_url": r.url,
                "installed": name in installed,
            })
    _marketplace_cache["skills"] = out
    _marketplace_cache["ts"] = now
    return {"skills": out}


@app.get("/api/marketplace/skill/{registry_name}/{skill_name}")
async def marketplace_skill_detail(registry_name: str, skill_name: str) -> dict:
    """Tek bir skill'in manifest detayını döner (preview için)."""
    registries = reg_mod.load_registries()
    target = next((r for r in registries if r.name == registry_name), None)
    if target is None:
        raise HTTPException(404, f"Registry yok: {registry_name}")
    try:
        content = reg_mod.fetch_skill_md(target.skill_md_url(skill_name))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    fm = parse_frontmatter(content) or {}
    perms = fm.get("permissions") or []
    if not isinstance(perms, list):
        perms = []
    valid, unknown, forbidden = validate_permissions([str(p) for p in perms])

    return {
        "name": str(fm.get("name", skill_name)),
        "version": str(fm.get("version", "0.0.0")),
        "description": str(fm.get("description", "")),
        "icon": str(fm.get("icon", "")),
        "example_prompt": str(fm.get("example_prompt", "")),
        "permissions": [
            {
                "name": p,
                "risk": (PERMISSION_RISK[p].value if p in PERMISSION_RISK else "unknown"),
            }
            for p in perms
        ],
        "forbidden": forbidden,
        "unknown_permissions": unknown,
        "raw_url": target.skill_md_url(skill_name),
        "registry": registry_name,
    }


@app.post("/api/marketplace/install")
async def marketplace_install(body: dict = Body(...)) -> dict:
    """Skill'i yükle. body: {'registry': 'miniagent', 'name': 'open-ports'}"""
    registry_name = body.get("registry", "")
    skill_name = body.get("name", "")
    if not registry_name or not skill_name:
        raise HTTPException(400, "registry ve name gerekli")

    registries = reg_mod.load_registries()
    target = next((r for r in registries if r.name == registry_name), None)
    if target is None:
        raise HTTPException(404, f"Registry yok: {registry_name}")

    try:
        content = reg_mod.fetch_skill_md(target.skill_md_url(skill_name))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    fm = parse_frontmatter(content) or {}
    perms = fm.get("permissions") or []
    if not isinstance(perms, list):
        perms = []
    _, _, forbidden = validate_permissions([str(p) for p in perms])
    if forbidden:
        raise HTTPException(
            403,
            f"Yasak permission içeriyor: {', '.join(forbidden)} — yüklenmedi.",
        )

    final_name = str(fm.get("name") or skill_name).strip()
    path = reg_mod.install_skill_md(final_name, content)
    # Cache'i invalidate et
    _marketplace_cache["skills"] = None
    return {"ok": True, "name": final_name, "path": str(path)}


@app.post("/api/marketplace/remove")
async def marketplace_remove(body: dict = Body(...)) -> dict:
    """Kullanıcı skill'ini kaldır. body: {'name': 'open-ports'}"""
    name = body.get("name", "")
    if not name:
        raise HTTPException(400, "name gerekli")
    removed = reg_mod.remove_user_skill(name)
    _marketplace_cache["skills"] = None
    return {"ok": removed, "name": name}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket handler.

    Mimari: kullanıcı mesajı geldiğinde agent loop'u BACKGROUND TASK'ta çalıştırırız;
    böylece main loop receive_json'a geri döner ve client'ın approval_response
    mesajını alabilir. Aksi takdirde agent thread approval beklerken WS receive
    yapılamadığından deadlock olur (v0.3.1 → v0.4.0 bug'ı, v0.4.1'de düzeltildi).
    """
    await ws.accept()
    catalog, _ = _collect_skills()
    model = os.environ.get("AJANOX_MODEL", DEFAULT_MODEL)
    history: list[dict] = []

    loop = asyncio.get_event_loop()
    broker = WebApprovalBroker(ws, loop)
    approval.set_handler(broker.request)
    send_lock = asyncio.Lock()  # WS send'leri serialize et — paralel task'lardan

    async def safe_send(payload: dict) -> None:
        async with send_lock:
            await ws.send_json(payload)

    async def stream_agent_events(user_input: str) -> None:
        """Agent loop'unu thread'de çalıştır, event'leri WS'e stream et."""
        nonlocal history
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
            except urllib.error.URLError as exc:
                event_q.put({
                    "type": "error",
                    "message": (
                        f"Ollama'ya bağlanılamıyor: {getattr(exc, 'reason', exc)}. "
                        "Ollama çalışıyor mu? (`ollama serve`)"
                    ),
                })
            except Exception as exc:  # noqa: BLE001
                event_q.put({"type": "error", "message": str(exc)})
            finally:
                event_q.put({"type": "done"})

        threading.Thread(target=runner, daemon=True).start()

        while True:
            event = await loop.run_in_executor(None, event_q.get)
            await safe_send(event)
            if event.get("type") == "done":
                break

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "reset":
                history = []
                approval.reset_session()
                await safe_send({"type": "reset_ok"})
                continue

            if msg_type == "approval_response":
                # Approval'ı resolve et — agent thread bekliyordu, devam edecek
                broker.resolve(data.get("request_id", ""), data.get("decision", "no"))
                continue

            if msg_type != "user_message":
                await safe_send(
                    {"type": "error", "message": f"Bilinmeyen mesaj tipi: {msg_type}"}
                )
                continue

            user_input = (data.get("content") or "").strip()
            if not user_input:
                continue

            # KRİTİK: stream_agent_events'i background task'ta başlat,
            # main loop receive_json'a geri dönsün — approval_response
            # mesajları işlenebilsin.
            asyncio.create_task(stream_agent_events(user_input))
    except WebSocketDisconnect:
        pass
    finally:
        approval.set_handler(None)
        approval.reset_session()


def start_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Sunucuyu başlat. Production: prod-grade WSGI değil, geliştirme modu."""
    uvicorn.run(app, host=host, port=port, log_level="info")
