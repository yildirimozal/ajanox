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

## ⚠️ Ön gereksinim: Ollama + Qwen 2.5 14B

Ajanox **LLM'i kendi makinende çalıştırır** — bu yüzden iki şey gerekli:

| | Ne | Niçin |
|---|---|---|
| **Ollama** | Yerel LLM runtime | Ajanox HTTP üzerinden konuşur (`localhost:11434`) |
| **Qwen 2.5 14B** | Türkçe + tool-calling odaklı model | Ajanox'un beyni; ~9 GB indirme, ~10 GB RAM gerekir |

### Kurulum (5 dakika)

```bash
# 1. Ollama
brew install ollama                                    # macOS
# Linux:
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Ollama'yı çalıştır (arka planda kalmalı)
ollama serve &                                         # veya menübar uygulaması

# 3. Modeli indir (~9 GB, 5-15 dakika)
ollama pull qwen2.5:14b

# 4. Ajanox kur
pip install 'ajanox[web]'

# 5. Başlat
ajanox          # terminal shell
ajanox web      # tarayıcı dashboard — http://localhost:8765
```

> Ajanox başlangıçta otomatik **health check** yapar — Ollama veya model
> eksikse net hata mesajı ve uygulanabilir talimat gösterir.

### Daha az RAM'li makinelerde (≤ 8 GB)

```bash
AJANOX_MODEL=qwen2.5:7b ajanox      # daha küçük model (~5 GB)
ollama pull qwen2.5:7b
```
Not: 7B model tool-calling'de %20-50 daha az tutarlı. 14B kullanım için 16 GB+ RAM önerilir.

İlk komutunu yaz: `İstanbul'da hava nasıl?` veya `Bilgisayarın durumu nasıl?`

### Sorun mu çıktı?

| Hata | Çözüm |
|---|---|
| `Ollama'ya bağlanılamıyor` | `ollama serve` çalıştır veya menübar uygulamasını aç |
| `'qwen2.5:14b' yüklü değil` | `ollama pull qwen2.5:14b` |
| `pip install 'ajanox[web]'` zsh hata | Tırnak şart (`[web]`'i shell glob sanıyor) |
| Web dashboard'da "Skill yükleniyor…" hiç bitmiyor | Server'ı kontrol et — terminal'de `ajanox web` çalışıyor olmalı |

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
| **Güvenlik** | Open Interpreter `rm -rf /` yapabilir | Android-modeli **permission + runtime onay + bash sandbox + domain allowlist + skill imzalama + tool-call verification + audit log** |
| **Lisans** | Çoğu kapalı (Apple Intelligence, Copilot+) | **Apache 2.0** — fork, ticari, ne istersen |

## Mimari

4 katman. Aşağıdan yukarı inşa edilir.

| Katman | Sorumluluk |
|---|---|
| **K3 — UI** | Doğal dil CLI shell, web dashboard, ileride REST API |
| **K2 — LLM beyin** | Skill matcher, agent loop, prompt-based tool calling, permission enforcement, audit |
| **K1 — Skill katmanı** | SKILL.md formatı + lazy-load loader + 14 permission seti |
| **K0 — OS kernel** | Linux/Darwin (dokunulmaz, üstüne inşa edilir) |

Detay: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) • [docs/SPEC.md](docs/SPEC.md) (Skill Spec v0.1) • [docs/SECURITY.md](docs/SECURITY.md) • [docs/yolculuk.md](docs/yolculuk.md) (24 saatte sıfırdan nasıl yapıldı)

> **OS-katmanı (v2.0) ayrı repo'da:** [ajanox-l2](https://github.com/yildirimozal/ajanox-l2) — Ubuntu 24.04 fork, kendi ISO + installer. Bu repo (`ajanox`) L3 (Python paketi) odaklı kalır.

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
- 🔄 **v2.0** — Ajanox Linux remix (Pop_OS modeli) — kendi installer, default shell · [ajanox-l2](https://github.com/yildirimozal/ajanox-l2) (ayrı repo)
- 🔄 **v3.0+** — eBPF + LSM ile kernel-derinliğinde policy enforcement

## Lisans + Katkı

[Apache 2.0](LICENSE). Issues + discussions: https://github.com/yildirimozal/ajanox

İlk public release: v0.2.1 (2026-05-21). Erken faz — geri bildirim çok değerli.

---

**Pitch tek cümleyle:** "Yerel + Türkçe + açık kaynak + güvenli agentic OS katmanı. Skill ekleyerek genişlet."
