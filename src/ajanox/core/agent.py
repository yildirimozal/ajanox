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
DEFAULT_MODEL = os.environ.get("AJANOX_MODEL", "qwen2.5:14b")
DEFAULT_MAX_ITER = 8
DEFAULT_TEMPERATURE = 0.2

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
    model: str = DEFAULT_MODEL,
    max_iter: int = DEFAULT_MAX_ITER,
) -> None:
    """Bir kullanıcı sorgusunu uçtan uca çalıştır."""
    matched_skill, score = find_best_match(user_input, catalog)
    match_hint = format_match_hint(matched_skill) if matched_skill and score >= 1 else ""
    if matched_skill:
        print(f"  [match] {matched_skill.name} (score={score})")

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
        {"role": "user", "content": user_input},
    ]

    for _ in range(max_iter):
        msg = chat(messages, model=model)
        content = (msg.get("content") or "").strip()
        messages.append({"role": "assistant", "content": content})

        tool_call = extract_tool_call(content)
        if not tool_call:
            clean = strip_tool_call_tags(content)
            print(f"\nAjanox: {clean}\n" if clean else "\n(Boş cevap)\n")
            return

        name = tool_call.get("name", "")
        args = tool_call.get("arguments", {}) or {}

        if name not in PRIMITIVES:
            result = f"Hata: '{name}' bilinmeyen tool."
            print(f"  [warn] unknown tool: {name}")
        elif not enforcer.enforce(
            active_skill, active_perms, name, args, skill_location=active_location
        ):
            result = (
                f"İzin reddedildi: '{name}' skill '{active_skill}' için izinli değil "
                f"(izinler: {list(active_perms) or '[]'})."
            )
            print(f"  [denied] {name} for skill={active_skill}")
        else:
            if name != "bash":
                print(f"  [tool] {name}({args})")
            try:
                result = PRIMITIVES[name](**args)
            except TypeError as exc:
                result = f"Hata: tool argümanları yanlış: {exc}"
            preview = str(result)[:120].replace("\n", " ")
            print(f"  [out ] {preview}{'…' if len(str(result)) > 120 else ''}")

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
