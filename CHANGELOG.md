# Changelog

Tüm önemli değişiklikler bu dosyada izlenir. [Keep a Changelog](https://keepachangelog.com)
formatı, [SemVer](https://semver.org) sürümleme.

## [Unreleased]

## [0.3.2] - 2026-05-21

### Eklendi
- **`check_ollama_health()` fonksiyonu** (`core/agent.py`) — Ollama erişilebilir mi,
  gerekli model yüklü mü kontrol eder; hata durumunda uygulanabilir talimat verir
- **CLI başlangıç health check'i** — `ajanox` ve `ajanox web` başlarken Ollama'yı
  kontrol eder, eksikse net hata + kurulum komutları gösterir (sessiz crash yok)
- **WebSocket'tan açık Ollama hatası** — runtime'da Ollama düşerse browser'a "Ollama'ya
  bağlanılamıyor: ollama serve çalıştır" mesajı gider
- **README'de prominent ön gereksinim bölümü** — Ollama + Qwen 2.5 14B niçin, nasıl,
  troubleshooting tablosu, düşük RAM'li makineler için `qwen2.5:7b` fallback talimatı

### Düzeltildi
- `pip install ajanox` → `ajanox` çalıştırılınca Ollama yoksa cryptic urllib traceback
  alıyordu. Artık tek satır net hata + kurulum komutu.
- Web dashboard'da Ollama runtime'da düşerse "Skill yükleniyor…" sonsuza dek kalıyordu.
  Artık modal/error gösterir.

## [0.3.1] - 2026-05-20

### Eklendi
- **Web-native approval modal** — yüksek/kritik risk komutlar artık tarayıcıda
  modal olarak çıkar; web kullanıcısı terminale bağımlı değil.
  - `approval.set_handler()` pluggable API — terminal'i geçersiz kılar
  - `web/server.py` içinde `WebApprovalBroker` — async event loop ↔ sync agent
    thread arası `threading.Event` + `run_coroutine_threadsafe` köprüsü
  - WebSocket mesaj tipleri: `approval_request` (server→client), `approval_response`
    (client→server) — `decision: yes | no | all`
  - Frontend modal (Vue 3): risk-tag renkli (high=turuncu, critical=kırmızı),
    komut preview, 3 buton (E / H / T-Tümü)
  - Bağlantı kopunca handler otomatik temizlenir (single-user assumption v0.3.x)
- 4 yeni unit test (toplam 80) — custom handler yes/no/all/exception senaryoları

### Düzeltildi
- v0.3.0'da yüksek risk skill'ler web'de stuck'a düşüyordu (terminal'i takip
  etmek gerekiyordu) — artık modal ile çözülür.

## [0.3.0] - 2026-05-20

### Eklendi
- **Web Dashboard MVP** (`ajanox web`) — tarayıcıdan kullanılabilir UI:
  - FastAPI + WebSocket backend (`src/ajanox/web/server.py`)
  - Vue 3 frontend (CDN, build pipeline yok), tek HTML dosyası
  - Skill panel (sol sidebar) — `/api/info` ile otomatik yüklenir
  - Chat akışı: real-time event stream (match → tool_call → tool_result → final)
  - Permission denied görsel (kırmızı kutu)
  - `/reset` butonu (multi-turn history sıfırlama)
  - Dark theme
  - `pip install ajanox[web]` opsiyonel deps (`fastapi>=0.110`, `uvicorn[standard]>=0.27`)
- `core/agent.py`'a `on_event` callback parametresi — agent loop event'leri stream eder
  (CLI'da print'ler aynı kalır, web mode'da WebSocket'a yollar)
- `cli/web.py` — `ajanox web --host --port --no-browser` komut handler

### v0.3.0'da bilinen kısıtlama
- **Approval HÂLÂ terminal'de** — yüksek risk komutlar (örn. `delete-old-logs`) için
  web kullanıcısı serverın çalıştığı terminali takip etmeli. Web-native approval
  modal v0.3.1'de gelecek.

## [0.2.1] - 2026-05-20

### Eklendi
- **Multi-turn conversation state** — REPL artık konuşma geçmişini hatırlar
  (sliding window: son 10 mesaj). "Listele... evet sil" gibi iki-turn akışlar
  doğal çalışır. `/reset` (veya `/yeni`, `/clear`) komutu history'yi sıfırlar.
- **Context-aware matcher** — kısa girdiler ("evet sil") için önceki turn'lerin
  context'i match'i kuvvetlendirir; skill bağlamı turn'lar arası korunur.
- **Brace-balanced parser** — `find ... -exec rm {} \;` gibi nested `{}`
  içeren komut argümanları artık doğru parse edilir.
- **Dangerous flag detection** (mini flag-level whitelist):
  - `find -delete`, `find -exec`, `find -execdir` → shell_unsafe (önce safe görünüyordu)
  - `sed -i`, `sed --in-place` → shell_unsafe
- **Yeni built-in skill: `system-info`** — uname + uptime + df çıktısını
  birleştirip Türkçe sistem raporu sunar. Permissions: `[shell_safe, system_info]`
- **Yeni built-in skill: `delete-old-logs`** — POC senaryosu: N günden eski log
  dosyalarını listeler ve siler. Permissions: `[shell_safe, shell_unsafe, file_write]`.
  Güvenlik katmanı (runtime approval) rm öncesi onay sorar.
- `ajanox skill init <name>` — yeni skill için boilerplate üretir
  - `--user` flag ile `~/.ajanox/skills/` altına kurar (default: `cwd/skills/`)
  - `--description "..."` ile non-interactive
- `ajanox skill list` — yüklü skill'leri tablo halinde gösterir (`--source all|system|user`)
- `ajanox skill check <path>` — SKILL.md'nin spec'e uyumunu doğrular:
  - Zorunlu alan kontrolü (name, version, description, ajanox, permissions)
  - kebab-case name + semver version
  - Yasak permission tespiti (sudo)
  - Bilinmeyen permission uyarısı
  - Önerilen alan + body bölümü uyarıları
- `ajanox skill migrate` — v1.0 için stub (henüz aktif değil)
- **+26 yeni unit test** (toplam 76)

### Değişti
- Test sayısı: 50 → 76
- Skill sayısı (built-in): 3 → 5

### Bilinen sınırlamalar v0.2.1'de
- Model bazen "echo 'silindi'" gibi yalancı çıktı verebilir (halüsinasyon);
  güvenlik açısından zararsız (gerçek aksiyon yapılmaz) ama UX kafa karışıklığı.
  v0.3'te tool-call verification katmanı eklenecek.
- pyproject.toml version 0.1.0 idi (v0.2.0'da unutulmuş), bu sürümde 0.2.1'e çekildi.

## [0.2.0] - 2026-05-20

İlk public release. POC fazı + güvenlik katmanı tamamlandı.

### Eklendi

#### Çekirdek (v0.1 → v0.2)
- **Skill sistemi** — `skills/<name>/SKILL.md` formatı, YAML frontmatter manifest
- **Lazy-load skill loader** — katalog sistem promptunda, body model çağırınca okunur
- **Prompt-based tool calling** — Ollama'nın native `tools` API'sine bağımsız;
  modelden bağımsız çalışır (qwen2.5:14b ile %100 başarı oranı)
- **Deterministik skill matching** (`core/matcher.py`) — kullanıcı girdisi keyword
  match ile uygun skill'e yönlendirilir; modelin "yanlış skill seçimi" sorununu çözer
- **Doğal dil CLI** — `ajanox` komutu Türkçe REPL açar

#### Güvenlik (v0.2'nin ana çıktısı)
- **Permission enforcement** (`core/enforcer.py`) — default-deny; skill'in
  manifest'inde olmayan permission'ı kullanamaz
- **Bash kategorize** — pipe segmentleri ayrı sınıflandırılır; en yüksek risk kazanır:
  - `shell_safe` (whitelist'teki 33 binary)
  - `network_read` / `network_write` (curl, wget, ping + POST/PUT/DELETE flag'leri)
  - `notification` (osascript, notify-send, terminal-notifier)
  - `shell_unsafe` (geri kalan her şey)
- **Runtime onay promptları** (`core/approval.py`) — yüksek/kritik risk için
  her çağrıda kullanıcıya görünür; E/H/T (Tümü-oturum-için) seçenekleri
- **Critical paths** — `~/.ssh`, `/etc`, `~/Library` gibi 26 yola yazma her zaman
  runtime onay ister
- **Self-introspection bypass** — skill kendi SKILL.md dosyasını okumak için
  permission gerekmiyor (lazy-load mimarisinin doğal gereksinimi)
- **Audit log** (`core/audit.py`) — `~/.ajanox/audit.log` JSON Lines formatında
  her tool çağrısı, ret, onay kayıt altında
- **sudo permission** v0.x boyunca yasak (Spec kararı, v1.0'da gelecek)

#### Doküman & Dağıtım
- `docs/SPEC.md` — Skill Spec v0.1 (14 permission, hibrit onay modeli, 8 karar)
- `docs/ARCHITECTURE.md` — 4 katmanlı mimari + veri akışı
- `docs/SECURITY.md` — tehdit modeli + savunma katmanları
- `docs/DEVELOPER.md` — skill yazma rehberi (10 dakika)
- Apache 2.0 License
- `pyproject.toml` ile pip-installable paket
- GitHub Actions CI (ubuntu + macos, Python 3.10-3.12)

#### Test
- 50 unit test (pytest)
- 15/15 end-to-end smoke test (weather + find-large-files + mac-notification)

### Bilinen sınırlamalar (v0.3+'a)
- **Multi-turn conversation yok** — her kullanıcı girdisi fresh conversation;
  `delete-old-logs` gibi iki-aşamalı skill'ler bazen tam tek turda çalışmaz
- Flag-level whitelist (`sed -i` vs `sed -n` ayrımı yok)
- Domain allowlist (network_read tüm internet'e açık)
- Skill imzalama (marketplace için)
- Sandbox default-on (şu an opt-in `AJANOX_SANDBOX=strict`)
- Audit log rotation
- Web dashboard
- REST API
- Sadece macOS + Linux test edildi; Windows WSL2 sonraki sürümde

### Gereksinimler
- Python 3.10+
- [Ollama](https://ollama.ai) + `qwen2.5:14b` model (~9 GB)
- macOS veya Linux

[Unreleased]: https://github.com/yildirimozal/ajanox/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/yildirimozal/ajanox/releases/tag/v0.2.0
