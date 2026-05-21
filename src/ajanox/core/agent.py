"""Ajanox agent loop.

LLM ile konuşur, çıktıdan tool çağrılarını parse eder, primitives'i
çalıştırır, sonucu modele geri verir. Provider-agnostic — Ollama'nın
tool API'sine bağımlı değildir, kendi prompt-based protokolünü kullanır.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from . import enforcer
from .matcher import find_best_match, format_match_hint
from .parser import extract_tool_call, strip_tool_call_tags
from .primitives import PRIMITIVES
from .skill_loader import Skill, format_skill_catalog, load_skill_catalog


# Match yokken kullanılan default permission seti.
# Ad-hoc kullanıcı sorguları için sadece read-only komutlara izin verilir.
DEFAULT_SYSTEM_PERMISSIONS: tuple[str, ...] = ("shell_safe", "file_read")
DEFAULT_SYSTEM_SKILL_NAME = "system"


OLLAMA_URL = os.environ.get("AJANOX_OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_BASE = OLLAMA_URL.rsplit("/api/", 1)[0] if "/api/" in OLLAMA_URL else "http://localhost:11434"
DEFAULT_MODEL = os.environ.get("AJANOX_MODEL", "qwen2.5:14b")
DEFAULT_MAX_ITER = 8
DEFAULT_TEMPERATURE = 0.2
DEFAULT_HISTORY_LIMIT = 10  # son N user/assistant mesajı (5 turn) — sliding window


def check_ollama_health(model: str | None = None, timeout: float = 5.0) -> tuple[bool, str]:
    """Ollama erişilebilir mi, gerekli model yüklü mü? (ok, mesaj) döner.

    Hata durumlarında kullanıcıya net, uygulanabilir talimatlar verir.
    """
    target_model = model or DEFAULT_MODEL
    tags_url = f"{OLLAMA_BASE}/api/tags"
    install_hint = (
        "  Kurulum:\n"
        "    macOS:  brew install ollama && ollama serve\n"
        "    Linux:  curl -fsSL https://ollama.ai/install.sh | sh\n"
        f"  Model:  ollama pull {target_model}"
    )

    try:
        with urllib.request.urlopen(tags_url, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as exc:
        return False, (
            f"✗ Ollama'ya bağlanılamıyor ({OLLAMA_BASE}): {getattr(exc, 'reason', exc)}\n"
            f"  Ollama çalışıyor mu? (Terminal: `ollama serve` veya menübar uygulaması)\n"
            + install_hint
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"✗ Ollama beklenmedik hata: {exc}\n" + install_hint

    models = [m.get("name", "") for m in data.get("models", [])]
    if target_model in models:
        return True, f"✓ Ollama hazır — {target_model} yüklü"

    # Ollama çalışıyor ama model yok
    available = ", ".join(sorted(models)) if models else "(hiç model yüklü değil)"
    return False, (
        f"✗ Ollama çalışıyor ama '{target_model}' yüklü değil.\n"
        f"  Mevcut modeller: {available}\n"
        f"  Yüklemek için: ollama pull {target_model}\n"
        f"  (Yaklaşık 9 GB indirme, 5-15 dakika alabilir)"
    )

TOOL_PROTOCOL_PROMPT = """
=== TOOL CALLING PROTOKOLÜ (ZORUNLU) ===

Bir tool çağırmak istediğinde, cevabını TAM olarak şu formatta yaz:

<tool_call>
{"name": "<tool_adı>", "arguments": {"<arg_adı>": "<değer>"}}
</tool_call>

KURALLAR:
- Tek seferde TEK tool. Birden fazla çağırma.
- JSON dışında BAŞKA HİÇBİR ŞEY yazma (selamlama yok, açıklama yok).
- JSON kesinlikle geçerli olmalı.
- Tool sonucu geldikten SONRA, ya başka bir tool çağır ya da kullanıcıya
  doğal Türkçe cevap ver (bu durumda <tool_call> ETİKETİ YOK).

Mevcut tool'lar:
  read_file(path: string) -> dosya içeriği
  list_files(directory: string) -> klasör listesi
  bash(command: string) -> shell komutu çıktısı
"""

SYSTEM_PROMPT_BASE = """Sen yardımcı bir Türkçe asistansın (Ajanox).

Elinde üç temel araç var: read_file, list_files, bash.
Yüklenebilen "skill"ler var (aşağıda katalog). Skill, belirli bir
görev için yazılmış Markdown talimat dosyasıdır.

Bir kullanıcı isteği için uygun bir skill varsa:
  1. Katalogdan doğru skill'i seç.
  2. `read_file` ile SKILL.md'yi oku.
  3. İçindeki komutu `bash` ile çalıştır (ezbere komut üretme).
  4. Tool sonucunu aldıktan sonra kullanıcıya doğal Türkçe cevap ver.

Skill yoksa kendi bilginle veya `bash` ile cevapla.
"""


OLLAMA_TIMEOUT = float(os.environ.get("AJANOX_OLLAMA_TIMEOUT", "60"))


def chat(messages: list[dict], model: str = DEFAULT_MODEL) -> dict:
    """Ollama chat endpoint'ine istek at. Tool parametresi YOLLAMA."""
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": DEFAULT_TEMPERATURE},
        }
    ).encode()
    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT) as response:
        return json.loads(response.read())["message"]


def run_agent(
    user_input: str,
    catalog: list[Skill],
    history: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    max_iter: int = DEFAULT_MAX_ITER,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    on_event=None,
) -> list[dict]:
    """Bir kullanıcı sorgusunu uçtan uca çalıştır.

    Args:
        user_input: bu turdaki kullanıcı mesajı
        catalog: yüklü skill'ler
        history: önceki user/assistant mesajları (tool çağrıları DAHİL DEĞİL).
            None ise boş başlar.
        model: Ollama model adı
        max_iter: tool-çağrı iterasyon limiti
        history_limit: sliding window — son N mesaj korunur

    Returns:
        Güncellenmiş history (bu turdaki user input + final assistant yanıtı
        eklenmiş; sliding window uygulanmış).
    """
    history = history or []

    # Multi-turn skill continuity: önceki turn'lerin user/assistant content'ini
    # matcher'a context olarak ver. "evet sil" gibi kısa girdilerde önceki
    # turn'de geçen skill match'i korunur.
    context_blob = " ".join(
        m.get("content", "") for m in history[-4:] if isinstance(m, dict)
    )
    matched_skill, score = find_best_match(user_input, catalog, context=context_blob)
    match_hint = format_match_hint(matched_skill) if matched_skill and score >= 1 else ""

    def emit(event: dict) -> None:
        """Web dashboard veya başka observer için event yolla."""
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    if matched_skill:
        print(f"  [match] {matched_skill.name} (score={score})")
        emit({"type": "match", "skill": matched_skill.name, "score": score})

    # Aktif güvenlik bağlamı: match varsa skill'in izinleri, yoksa sistem defaults
    if matched_skill:
        active_skill = matched_skill.name
        active_perms: tuple[str, ...] = matched_skill.permissions or ()
        active_location: str | None = matched_skill.location
    else:
        active_skill = DEFAULT_SYSTEM_SKILL_NAME
        active_perms = DEFAULT_SYSTEM_PERMISSIONS
        active_location = None

    system_prompt = (
        SYSTEM_PROMPT_BASE
        + format_skill_catalog(catalog)
        + match_hint
        + TOOL_PROTOCOL_PROMPT
    )
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *history,  # önceki turn'lerin user/assistant mesajları
        {"role": "user", "content": user_input},
    ]
    final_response = ""

    for _ in range(max_iter):
        msg = chat(messages, model=model)
        content = (msg.get("content") or "").strip()
        messages.append({"role": "assistant", "content": content})

        tool_call = extract_tool_call(content)
        if not tool_call:
            final_response = strip_tool_call_tags(content)
            print(
                f"\nAjanox: {final_response}\n" if final_response else "\n(Boş cevap)\n"
            )
            emit({"type": "final", "content": final_response})
            return _trimmed(history, user_input, final_response, history_limit)

        name = tool_call.get("name", "")
        args = tool_call.get("arguments", {}) or {}

        if name not in PRIMITIVES:
            result = f"Hata: '{name}' bilinmeyen tool."
            print(f"  [warn] unknown tool: {name}")
            emit({"type": "warn", "message": f"unknown tool: {name}"})
        elif not enforcer.enforce(
            active_skill, active_perms, name, args, skill_location=active_location
        ):
            result = (
                f"İzin reddedildi: '{name}' skill '{active_skill}' için izinli değil "
                f"(izinler: {list(active_perms) or '[]'})."
            )
            print(f"  [denied] {name} for skill={active_skill}")
            emit({"type": "denied", "tool": name, "skill": active_skill})
        else:
            if name != "bash":
                print(f"  [tool] {name}({args})")
            emit({"type": "tool_call", "tool": name, "args": args})
            try:
                result = PRIMITIVES[name](**args)
            except TypeError as exc:
                result = f"Hata: tool argümanları yanlış: {exc}"
            preview = str(result)[:120].replace("\n", " ")
            print(f"  [out ] {preview}{'…' if len(str(result)) > 120 else ''}")
            emit({"type": "tool_result", "tool": name, "output": str(result)[:1000]})

        messages.append(
            {"role": "user", "content": f"[TOOL RESULT - {name}]\n{result}"}
        )

        if name == "read_file" and "SKILL.md" in str(args.get("path", "")):
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "[SİSTEM] SKILL.md içeriğini aldın. ŞİMDİ uygun komutu "
                        "`bash` tool'u ile çalıştır. Komutu sadece açıklama, "
                        "gerçekten çalıştır. Tool call formatını hatırla."
                    ),
                }
            )

    print("\n(Max iterasyon aşıldı.)\n")
    return _trimmed(history, user_input, final_response, history_limit)


def _trimmed(
    prior_history: list[dict],
    user_input: str,
    assistant_response: str,
    limit: int,
) -> list[dict]:
    """Yeni history hesapla + sliding window uygula.

    Tool çağrılarını history'e koyma — sadece düz user/assistant pair'leri.
    Bu context window'u şişirmemek için kritik.
    """
    new = list(prior_history)
    new.append({"role": "user", "content": user_input})
    if assistant_response:
        new.append({"role": "assistant", "content": assistant_response})
    if limit > 0 and len(new) > limit:
        new = new[-limit:]
    return new
