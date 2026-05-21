# Changelog

Tüm önemli değişiklikler bu dosyada izlenir. [Keep a Changelog](https://keepachangelog.com)
formatı, [SemVer](https://semver.org) sürümleme.

## [Unreleased]

## [0.4.4] - 2026-05-21

### Eklendi
- **Skill paneli VS Code tarzı kartlar**:
  - Her skill için **ikon** (emoji veya manifest'ten `icon`)
  - Hover/active görsel feedback
  - **Tıklanabilir** — kartın `example_prompt`'unu otomatik gönderir
  - Kartta "▸ örnek prompt" ipucu (yeşil, italik)
  - thinking sırasında disabled state (soluk + cursor not-allowed)
- Skill manifest'ine 2 yeni opsiyonel alan:
  - `icon: "🌤️"` — UI'da gösterilecek emoji veya path
  - `example_prompt: "İstanbul'da hava nasıl?"` — kart tıklanınca gönderilir
- 5 builtin skill'in tamamına icon + example_prompt eklendi
- `Skill` dataclass'ına `icon` ve `example_prompt` field'ları
- Fallback emoji map (manifest icon'u yoksa name'den tahmin)

### Düzeltildi
- **Skill listesi dedup** — aynı skill name birden fazla kaynaktan (örn.
  builtin + cwd/skills) gelirse panelde **tek kez** görünür. Daha önce
  duplikatlar gözüküyordu.

## [0.4.3] - 2026-05-21

### Eklendi
- **Streaming cevap üretimi** — Ollama `stream=true` ile token-by-token UI:
  - `chat_stream()` core/agent.py'a eklendi
  - `assistant_chunk` event'i her token deltası için emit edilir
  - UI'da yanıp sönen `▍` cursor ile aktif streaming gösterilir
  - Tool call algılandıysa `assistant_chunk_cancel` ile baloncuk silinir,
    normal tool akışına döner
  - **Perceived latency 80% düşer**: ilk token ~1-2 sn'de, kullanıcı donmuş hissetmez
- **Tool çıktısı görünür** — bash/curl/lsof sonuçları artık mesaj listesinde
  kompakt monospace yeşil-kenarlı kutuda görünüyor. Match/tool_call hâlâ
  accordion'da (gürültü değil).

### Test
- chat_stream() E2E: 'kısa selamlama' → 10 chunk → "Merhaba..."

## [0.4.2] - 2026-05-21

### Değişti
- **Web UI temizliği** — intermediate event'ler (match, tool_call, tool_result)
  artık mesaj listesinde gözükmüyor:
  - Sadece kullanıcı + Ajanox final cevabı + güvenlik mesajları (denied/warn) görünür
  - Status bar'da current activity (`weather: curl wttr.in/...`) + saniye sayacı
  - Final cevabın altında "Detaylar (N adım) ▸" accordion ile tüm event akışı
- Default Ollama health-check timeout: 3s → 5s (ilk request bazen yavaş)

### Düzeltildi
- Health check'in ilk request'te 3s'i aşması durumunda server başlamıyordu.
  Artık 5s default; `AJANOX_OLLAMA_TIMEOUT` env var ile özelleştirilebilir.

## [0.4.1] - 2026-05-21

### Düzeltildi
- **KRİTİK web deadlock**: Yüksek/kritik risk komutlar veya legacy mode'da, agent thread
  approval beklerken WS handler client'ın `approval_response` mesajını alamıyordu
  (agent thread'i sync olarak bekliyordu, event loop bloklu). Sonuç: 120s timeout,
  broker "no" döndü, kullanıcı tarayıcıda modal'da "evet" tıklasa bile **DENIED**.
  - Düzeltme: `stream_agent_events()` artık `asyncio.create_task()` ile background'a
    alınır. Main loop `receive_json`'a geri döner; approval mesajları işlenebilir.
  - `asyncio.Lock` ile WS send'leri serialize edildi (paralel task'lardan korunmak için).

### Eklendi
- **Legacy mode** — manifest'te `permissions: []` veya hiç permission yoksa skill
  artık reddedilmiyor; her tool çağrısı için **runtime onay** zorlanır.
  - Marketplace'ten yüklenen v0.x öncesi format (`miniagent` skill'leri gibi) artık
    "untrusted" davranışıyla çalışır — her komut görünür modal ister.
  - Install'da net uyarı: "BELIRTILMEMIŞ — legacy mode" + "her çağrı için onay"
- 2 yeni unit test (toplam 97).

## [0.4.0] - 2026-05-21

### Eklendi
- **Skill Marketplace MVP** — GitHub-tabanlı uzak skill yükleme:
  - `ajanox skill install <spec>` — registry/URL/shorthand'den yükle
  - `ajanox skill remove <name>` — kullanıcı skill'ini kaldır
  - `ajanox skill search [query]` — registry'lerdeki skill'leri listele
- Üç format desteklenir:
  - **Bare name**: `ajanox skill install open-ports` (default registry'den)
  - **Shorthand**: `ajanox skill install user/repo:skill-name`
  - **Tam URL**: `https://github.com/user/repo/tree/branch/skills/name`
- **Default registry**: `yildirimozal/miniagent` — önceden kayıtlı, 8 skill içeriyor
  (git-log, ip-location, json-format, open-ports vs.)
- `~/.ajanox/registries.json` — kayıtlı registry'ler (otomatik oluşur)
- Yükleme akışı **güvenlik-öncelikli**:
  - Untrusted kaynak işareti
  - Yüksek/kritik risk izinler `⚠` ile vurgulanır
  - `sudo` gibi yasak permission → kurulum REDDEDİLİR
  - Bilinmeyen izin → uyarı
  - Default'ta onay sorulur (`--yes` ile script modu)
- 15 yeni unit test (toplam 95)
- `core/registry.py` — Registry, SkillSpec, fetch_skill_md, list_registry_skills

### Bilinen sınırlamalar
- Versioning yok (her zaman latest çekilir) — v0.4.1'de `name@version` formatı eklenecek
- Registry yönetimi (`add/remove`) — şu an `~/.ajanox/registries.json` elle düzenleniyor
- Skill signing yok (v1.0+ için)
- Untrusted bayrağı runtime'da kullanılmıyor — sadece install görünür uyarı

## [0.3.3] - 2026-05-21

### Düzeltildi
- **KRİTİK**: Dev install (`pip install -e .`) modunda `_builtin_skills_dir()` paket
  içindeki `builtin_skills/` klasörünü arıyordu (sadece wheel build'de oluşur).
  Bu mod hiç skill yüklemiyordu → matcher boş katalogda match aramıyor → "system"
  pseudo-skill devreye giriyor → `curl` shell_unsafe → permission denied →
  **model halüsinasyon yapıyordu** ("API anahtarı engellendi" gibi yalanlar).
- Dev install için fallback: repo root'taki `skills/` klasörü kullanılır.
- Bu fix `cli/shell.py` ve `cli/skill.py`'da uygulandı.

### Etkileyen senaryolar
- `pip install -e .` ile geliştiren kişiler (skill 0)
- `pip install ajanox` yapan kullanıcılar etkilenmedi (wheel'de builtin_skills içeride)

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
