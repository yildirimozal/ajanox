# Ajanox

> **Türkçe doğal dil komutlarıyla çalışan, ajan tabanlı, açık kaynak işletim sistemi katmanı.**
> Tamamen yerel — verin makinende kalır. Skill ekleyerek genişlet.

[![PyPI version](https://img.shields.io/pypi/v/ajanox.svg)](https://pypi.org/project/ajanox/)
[![Python](https://img.shields.io/pypi/pyversions/ajanox.svg)](https://pypi.org/project/ajanox/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-80%2F80-brightgreen)](tests/)

---

## Ne yapar?

Türkçe yazarsın — Ajanox uygun skill'i bulur, güvenlik onayını alır, çalıştırır.

```
Sen: 30 günden eski log dosyalarını sil

Ajanox 🔧 delete-old-logs
  [bash] find /tmp/logs -name "*.log" -mtime +30
  [out ] /tmp/logs/old1.log /tmp/logs/old2.log /tmp/logs/old3.log

  ┌─ Güvenlik Onayı ────────────────────────
  │ Skill:   delete-old-logs
  │ Komut:   rm -f /tmp/logs/old1.log /tmp/logs/old2.log ...
  │ Risk:    shell_unsafe
  │ [E]vet  [H]ayır  [T]ümünü bu oturum
  └──────────────────────────────────────────
> e

  [bash] rm -f /tmp/logs/old1.log ...
  3 dosya silindi.
```

## 5 dakikada kurulum

```bash
# 1. Ollama + model (~9 GB, bir kere)
brew install ollama && ollama pull qwen2.5:14b   # macOS
# (Linux: curl -fsSL https://ollama.ai/install.sh | sh && ollama pull qwen2.5:14b)

# 2. Ajanox
pip install 'ajanox[web]'

# 3. Başlat
ajanox          # terminal shell
ajanox web      # tarayıcı dashboard — http://localhost:8765
```

İlk komutunu yaz: `İstanbul'da hava nasıl?` veya `Bilgisayarın durumu nasıl?`

## Yerleşik skill'ler (v0.3.1)

| Skill | Ne yapar | Permissions |
|---|---|---|
| `weather` | Şehir bazlı hava durumu (wttr.in) | `shell_safe`, `network_read` |
| `find-large-files` | Klasördeki en büyük dosyaları listele (`du`) | `shell_safe`, `file_read` |
| `system-info` | OS + uptime + disk raporu | `shell_safe`, `system_info` |
| `mac-notification` | macOS masaüstü bildirimi | `shell_safe`, `notification` |
| `delete-old-logs` | N günden eski log dosyalarını sil (runtime onay) | `shell_safe`, `shell_unsafe`, `file_write` |

`ajanox skill list` ile gör.

## Niçin Ajanox?

| | Diğerleri | Ajanox |
|---|---|---|
| **Veri** | Cloud API'lere gider (Claude, OpenAI) | Makinende kalır, **internet gerekmez** |
| **Dil** | İngilizce-öncelik | **Türkçe-öncelik** + İngilizce |
| **Genişleme** | Kod yazmak gerek | **Markdown skill** — Python öğrenmesen de yaz |
| **Güvenlik** | Open Interpreter `rm -rf /` yapabilir | Android-modeli **permission + runtime onay + audit log** |
| **Lisans** | Çoğu kapalı (Apple Intelligence, Copilot+) | **Apache 2.0** — fork, ticari, ne istersen |

## Mimari

4 katman. Aşağıdan yukarı inşa edilir.

| Katman | Sorumluluk |
|---|---|
| **K3 — UI** | Doğal dil CLI shell, web dashboard, ileride REST API |
| **K2 — LLM beyin** | Skill matcher, agent loop, prompt-based tool calling, permission enforcement, audit |
| **K1 — Skill katmanı** | SKILL.md formatı + lazy-load loader + 14 permission seti |
| **K0 — OS kernel** | Linux/Darwin (dokunulmaz, üstüne inşa edilir) |

Detay: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) • [docs/SPEC.md](docs/SPEC.md) (Skill Spec v0.1) • [docs/SECURITY.md](docs/SECURITY.md)

## Skill yazmak

5 dakika, kod gerek değil:

```bash
ajanox skill init my-skill --description "Ne yapar bir cümle"
$EDITOR skills/my-skill/SKILL.md
ajanox skill check skills/my-skill
ajanox  # REPL'de dene
```

Detaylı rehber: [docs/DEVELOPER.md](docs/DEVELOPER.md)

## Gereksinimler

- Python 3.10+
- [Ollama](https://ollama.ai) + `qwen2.5:14b` (~9 GB RAM)
- macOS veya Linux (Windows WSL2 yakında)

## Yol haritası

- ✅ **v0.2.x** — CLI + skill sistemi + güvenlik
- ✅ **v0.3.x** — Web dashboard + approval modal
- 🔄 **v1.0** — API stabilizasyonu, ekosistem, dokümantasyon
- 🔄 **v2.0** — Ajanox Linux remix (Pop_OS modeli) — kendi installer, default shell
- 🔄 **v3.0+** — eBPF + LSM ile kernel-derinliğinde policy enforcement

## Lisans + Katkı

[Apache 2.0](LICENSE). Issues + discussions: https://github.com/yildirimozal/ajanox

İlk public release: v0.2.1 (2026-05-21). Erken faz — geri bildirim çok değerli.

---

**Pitch tek cümleyle:** "Yerel + Türkçe + açık kaynak + güvenli agentic OS katmanı. Skill ekleyerek genişlet."
