# Ajanox

> Türkçe doğal dil komutlarıyla çalışan, ajan tabanlı, açık kaynak işletim sistemi katmanı.

**Status:** v0.1 erken geliştirme. POC fazında. Henüz production-ready değil.

---

## Ne yapar?

Linux veya macOS'a kurulur. Doğal Türkçe (veya İngilizce) yazarsınız, Ajanox uygun ajanı/skill'i seçer ve sizin için işi yapar:

```
Sen: 30 günden eski log dosyalarını sil
Ajanox: ~/logs altında 12 dosya bulundu. Silme öncesi onaylar mısın? [E/H]
Sen: E
Ajanox: 12 dosya silindi (toplam 340 MB).
```

## Mimari (4 katman)

| Katman | Ne yapar |
|---|---|
| **K3 — UI** | Doğal dil shell, web dashboard, REST API |
| **K2 — LLM beyin** | Görevi parçalar, doğru skill'i seçer, sonucu sentezler, güvenlik kontrolü |
| **K1 — Sistem ajanları + skill'ler** | FileAgent, ProcAgent, NetAgent, MonitorAgent + topluluk skill'leri |
| **K0 — OS kernel** | Linux/Darwin — dokunulmaz, üstüne inşa edilir |

Detaylı mimari: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Kurulum (geliştirme)

Henüz paket yok. Şimdilik:

```bash
git clone https://github.com/yildirimozal/ajanox.git
cd ajanox

# Virtual environment (önerilir — sistem Python'unu kirletmemek için)
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
ajanox
```

**Gereksinimler:**
- Python 3.10+
- [Ollama](https://ollama.ai) + `qwen2.5:14b` model
- macOS veya Linux (Windows: WSL2 v0.5+)

```bash
# Modeli indir (yaklaşık 9 GB)
ollama pull qwen2.5:14b
```

## Test çalıştır

```bash
pytest -v
```

12 birim test, ~0.02s. Faz B (proje iskeleti) tamamlandığında 12/12 geçiyor.

## Skill yazmak

Skill = bir Markdown dosyası. Spec: [docs/SPEC.md](docs/SPEC.md).

```markdown
---
name: my-skill
version: 0.1.0
description: Bu skill ne yapar (1 cümle)
permissions: [shell_safe]
ajanox: ">=0.1.0 <1.0.0"
---

# My Skill

## Çalıştırılacak komut
\`\`\`bash
echo "merhaba"
\`\`\`
```

Detaylı rehber: [docs/DEVELOPER.md](docs/DEVELOPER.md)

## Lisans

[Apache 2.0](LICENSE)

## Katkı

Henüz erken faz. Issues + discussions için: https://github.com/yildirimozal/ajanox
