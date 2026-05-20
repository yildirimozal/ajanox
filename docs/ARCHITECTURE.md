# Ajanox Mimarisi

> **Versiyon:** v0.1 — POC fazı

## 4 Katmanlı Yapı

```
┌─────────────────────────────────────────────────────────────┐
│  Kullanıcı: "30 günden eski log dosyalarını sil"            │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─── K3 ── Kullanıcı Arayüzü ─────────────────────────────────┐
│  • Doğal dil shell  (v0.1: aktif)                           │
│  • Web dashboard    (v0.2+)                                 │
│  • REST API         (v0.3+)                                 │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─── K2 ── LLM Orkestratör (Beyin) ───────────────────────────┐
│  • Task planner       — komutu ajan çağrılarına böler        │
│  • Agent router       — doğru skill'i seçer                  │
│  • Result synthesizer — çıktıları akıcı Türkçe'ye dönüştürür  │
│  • Safety guard       — runtime permission onayı             │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─── K1 ── Sistem Ajanları + Skill'ler ───────────────────────┐
│  Primitives (her zaman yüklü):                              │
│    • read_file, list_files, bash                            │
│                                                             │
│  Skill'ler (Markdown talimat dosyaları):                    │
│    • Built-in: weather, find-large-files, mac-notification  │
│    • Topluluk: Ajanox Skill Spec v0.1'e uygun her şey       │
│                                                             │
│  Ajan'lar (v0.2+, ileride):                                 │
│    • FileAgent, ProcAgent, NetAgent, MonitorAgent           │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─── K0 ── OS Kernel ─────────────────────────────────────────┐
│  Linux / macOS Darwin / (gelecek: WSL2)                     │
│  Dokunulmaz — Ajanox üstüne inşa edilir, değiştirmez.       │
└─────────────────────────────────────────────────────────────┘
```

## Veri akışı: bir istek nasıl işlenir?

1. **K3 → K2:** Kullanıcı yazdığı doğal dil komutu K2'ye iletilir.
2. **K2'de:** LLM, sistem promptunda mevcut skill kataloğunu görür. Uygun bir skill varsa onu seçer.
3. **K2 → K1:** `read_file` ile SKILL.md okunur (lazy load).
4. **K2'de devam:** SKILL.md'deki talimatlara göre `bash` (veya başka primitive) çağrısı planlanır.
5. **Permission kontrolü:** Çağrılacak primitive'in permission seviyesi yüksek/kritik ise kullanıcıya runtime onayı sorulur.
6. **K1 → K0:** Primitive, OS kernel'ine syscall yapar (read, exec, vs.).
7. **K0 → K1 → K2:** Sonuç geriye akar.
8. **K2'de sentez:** Sonuç akıcı Türkçe ile formatlanır.
9. **K2 → K3 → Kullanıcı:** Cevap görüntülenir.

## Tool-calling protokolü

Ajanox, modelin native function-calling API'sine bağımlı **değildir**. Bunun yerine
prompt-based protokol kullanılır: sistem promptunda `<tool_call>{json}</tool_call>`
format tarif edilir, model çıktısı `core/parser.py` ile parse edilir.

**Sebep:** Smoke testte (2026-05-20) gözlemlendiği üzere, Ollama'nın native `tools`
parametresi modellere göre kırılgan (qwen2.5:7b %20, qwen2.5:14b %20, qwen2.5-coder
%0 başarı). Aynı modellerde prompt-based yaklaşımla %100 başarı elde edildi (14B
için). Bu yaklaşım model-bağımsız: Llama, Mistral, GPT, Claude — hepsinde aynı kod
çalışır.

## Modüler yapı

```
src/ajanox/
├── core/
│   ├── parser.py        — tool-call JSON parse
│   ├── primitives.py    — read_file, list_files, bash
│   ├── skill_loader.py  — SKILL.md katalog yükleyici
│   ├── agent.py         — agent loop (chat + dispatch)
│   ├── permissions.py   — permission yönetimi (v0.1 stub, v0.2 dolu)
│   └── whitelist.yml    — shell_safe komut listesi
└── cli/
    ├── __main__.py      — entry point
    ├── shell.py         — doğal dil REPL
    └── skill.py         — `ajanox skill ...` subcommands
```

## Yol haritası

- **v0.1** (şimdi): Tek dosyalık REPL, prompt-based tool calling, 3 built-in skill
- **v0.2**: Permission sistemi tam (Faz C), CLI subcommands dolu (`skill init/check`)
- **v0.3**: Web dashboard (FastAPI), REST API
- **v0.4**: Provider abstraction (Ollama + Claude + GPT fallback)
- **v0.5**: Skill marketplace (web)
- **v1.0**: Stable spec, breaking changes son
- **v2.x**: Ubuntu remix distro
