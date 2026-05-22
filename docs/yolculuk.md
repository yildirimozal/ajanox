# Ajanox — Bir günde sıfırdan agentic OS layer

> **Boş klasör → public PyPI paketi**, 24 saat. Bu, solo bir geliştiricinin
> (Özal Yıldırım) bir AI asistanı (Claude Opus 4.7) ile birlikte
> 2026-05-20/21'de yaptığı yolculuğun belgesi. Kararlar, bug'lar, sayılar.

---

## TL;DR

| | |
|---|---|
| **Başlangıç** | 2026-05-19, `~/Desktop/Projeler/AgenticOS/` boş klasör |
| **24 saat sonra** | PyPI'da `ajanox` v0.5.0, GitHub public repo, çalışan web dashboard + skill marketplace |
| **12 release** | v0.2.0 → v0.5.0 (sıfırdan) |
| **Test coverage** | 97/97 unit + 15/15 smoke = %100 |
| **Kod** | ~3500 satır Python + ~700 satır HTML/JS/CSS |
| **Mimari** | 4 katman (UI / LLM beyin / skills / OS kernel) |
| **Lisans** | Apache 2.0 |
| **Stack** | Python 3.10+ • Ollama • Qwen 2.5 14B • FastAPI • Vue 3 |

---

## 1. Başlangıç: Boş klasör, büyük vizyon

İlk konuşma 2026-05-19'da başladı. Kullanıcının zihninde 4 katmanlı bir mimari
diyagramı vardı:

```
Kullanıcı: "30 günden eski log dosyalarını sil"
              ↓
K3 — Kullanıcı arayüzü (Doğal dil shell, Web dashboard, REST API)
              ↓
K2 — LLM orkestratör (Task planner, Agent router, Result synthesizer, Safety guard)
              ↓
K1 — Sistem ajanları (FileAgent, ProcAgent, NetAgent, MonitorAgent)
              ↓
K0 — Linux kernel (gerçek — dokunulmaz, üstüne inşa edilir)
```

**Hedef:** Türkçe doğal dil ile çalışan, **Ubuntu gibi geniş kitleye ulaşabilen**,
**açık kaynak**, **geliştiricilerin SKILL.md eklediği** bir agentic OS katmanı.

**Adı:** Önce AgenticOS, sonra `agentros` (ROS = Robot Operating System ile
çakışma nedeniyle iptal), nihayet **Ajanox** ("ajan" + "ox") — kısa, global
telaffuz dostu, domain müsait (ajanox.com/dev), PyPI/GitHub'da boş.

---

## 2. İlk Mimari Kararlar (Faz 0)

24 saat sonra geçerli kalacak kritik kararlar:

| Konu | Karar | Niçin |
|---|---|---|
| **LLM** | Yerel — Ollama + Qwen 2.5 14B | Veri makinede kalır, internetsiz çalışır, API key/maliyet yok |
| **Platform** | Cross-platform (macOS + Linux + ileride WSL2) | Geniş kullanıcı tabanı |
| **Dağıtım hedefi** | Üst-katman paketi (v1.0) → Ubuntu remix (v2.0+) | Pop_OS modeli: önce ekosistem, sonra distro |
| **Hedef kitle** | Genel kullanıcı (Ubuntu hedef kitlesi) | GUI + Web dashboard + Türkçe |
| **Lisans** | Apache 2.0 | Patent koruması + kurumsal kabul |
| **Geliştirme dili** | Python | Hızlı, esnek, Ollama ile uyumlu |
| **Build pattern** | Alttan yukarı (K1 → K2 → K3) | Önce somut ajanlar, sonra orkestratör, sonra UI |

**Önemli prensip:** Sıfırdan kernel **yapmadık**. L3 (mevcut OS üstüne katman)
ile başladık çünkü Linux'un 30 milyon satır kodunu yeniden yazmak solo
geliştirici için imkansız. Bu, doğru bir trade-off — ekosistem inovasyonu
kernel inovasyonundan değerli.

---

## 3. Kritik Bulgu #1: Ollama Tool API Güvenilmez

İlk gün ciddi bir sürprize uğradık. **Smoke test sonuçları:**

| Model + Yaklaşım | Başarı |
|---|---|
| qwen2.5:7b + Ollama native tool API | **%20** (2/10) |
| qwen2.5-coder:7b + Ollama tool API | **%0** (JSON'u text olarak yazıyor) |
| qwen2.5:14b + Ollama tool API | %20 (model JSON üretiyor, Ollama parse etmiyor) |
| **qwen2.5:14b + prompt-based protokol** | **%100** (10/10) ✨ |

**Ders:** Ollama'nın `tools` parametresine güven olmaz. Her modelde farklı
davranır (qwen-base destekliyor, qwen-coder desteklemiyor, 14B kendi format'ı
zorluyor). Çözüm: **kendi prompt-based tool-calling protokolümüz** —
`<tool_call>{...}</tool_call>` formatı sistem promptunda tarif et, çıktıdan
manuel parse et.

**Bu mimari karar Ajanox'un kendine özgü farkı oldu:** model-bağımsız agent
loop. Yarın Llama 5 çıksa, Claude API'ye fallback eklensek — aynı kod çalışır.

---

## 4. Kritik Bulgu #2: Matcher Breakthrough (%40 → %100)

LLM'in en zayıf yetkinliği "doğru skill'i seçme". Web dashboard'da deneme
sırasında **%40 başarı** gözledik — model bazen skill ismini tool sanıyor,
bazen "yapamam" diyerek skill'i hiç denemiyor.

**Çözüm:** `core/matcher.py` — Python'da keyword matching ile **deterministik
skill seçimi**. Türkçe ek toleranslı prefix match (4+ harf):

```python
"İstanbul'da hava nasıl?" → tokenize → {istanbul, hava}
weather.description → {şehrin, güncel, hava, durumunu}
intersection = {hava} → score=1 → weather skill seçilir
```

Modele `format_match_hint(weather)` ile sistem promptunda **emir** verir:
> UYGUN SKILL TESPİT EDİLDİ: weather → bu yolu izle.

**Sonuç:** 15/15 başarı = **%100**. Aynı senaryoyu LLM'e bırakırsak %40,
Python deterministik matching ile %100.

**Mimari prensip:** *LLM'i sadece güvenilir olduğu yerde kullan: doğal dil
üretimi, parametre çıkarımı, tool argümanı doldurma. Karar/seçim katmanını
deterministik tut: skill matching, permission kontrolü, validation.*

---

## 5. Güvenlik Katmanı: Spec → Implementation

Hedef "genel kullanıcı kitlesi" olduğu için güvenlik artık opsiyonel değil.

### Skill Spec v0.1 — 8 karar (kullanıcı tartışmaları)

| # | Konu | Karar |
|---|---|---|
| A | `lib/` script izni | İzinli, `lib_execute` permission |
| B1 | Permission seti | 14 permission, Android tarzı (file_read, shell_safe, network_read…) |
| B2 | Onay zamanı | Hibrit: install (düşük risk) + runtime (yüksek risk) |
| B3 | Permission evrimi | Ekleme breaking değil, kaldırma major bump |
| C | Multi-version | Yok — tek skill tek sürüm |
| D | Body zorunlu yapı | Sadece öneri, linter raporlar |
| E | Geriye uyum | v0.x boyunca; v1.0'da kırılma |

### v0.2 Güvenlik implementasyonu (~700 satır)

- `core/permissions.py` — 14 permission, risk seviyeleri, sudo yasağı
- `core/enforcer.py` — default-deny, bash kategorize, critical path tespiti
- `core/approval.py` — runtime prompt + pluggable handler
- `core/audit.py` — JSON Lines logger, her aksiyon kayıt altında
- `core/critical_paths.yml` — 26 yol (`~/.ssh`, `/etc`, `~/Library`)
- `core/whitelist.yml` — 33 shell_safe binary

50 unit + 15 smoke test. **`sudo` permission v0.x boyunca yasak** — manifest'te
geçerse skill yüklenmez.

---

## 6. v0.2.x — Çekirdek (06:27 UTC)

```
v0.2.0  →  v0.2.1
ilk release    multi-turn + parser fix + dangerous flag + PyPI yayını
```

### v0.2.1 — Türkiye saatiyle sabah 09:27'de PyPI'da

```bash
pip install ajanox   # ← bu komut artık dünyaya açık
```

Yeni kullanıcı 5 dakikada kuruyor: Ollama → Qwen pull → pip install → çalışır.

5 built-in skill paket içinde:
- `weather` 🌤️
- `find-large-files` 📂
- `mac-notification` 🔔
- `system-info` 📊
- `delete-old-logs` 🗑️ (POC senaryomuz!)

---

## 7. v0.3.x — Web Dashboard (10:00–13:00 UTC)

CLI "developer oyuncağı" olarak kalmamak için tarayıcıda kullanılabilir UI.

### v0.3.0 — `ajanox web` çalışıyor

- **FastAPI + WebSocket** backend (~150 satır)
- **Vue 3 (CDN)** frontend, build pipeline yok (`index.html` tek dosya)
- Chat akışı, skill panel, permission denied görseli, dark theme

### v0.3.1 — Web-native approval modal

Sorun: yüksek risk komutlarda kullanıcı terminal'i takip etmek zorundaydı
(approval prompt orada). Çözüm: **WebApprovalBroker** — async event loop ↔ sync
agent thread arası `threading.Event` + `run_coroutine_threadsafe` köprüsü.
Approval artık tarayıcıda modal.

**Pluggable approval pattern:** `approval.set_handler(callable)` — herhangi
bir UI (web, desktop, mobil) terminal prompt'unu geçersiz kılabilir.

### v0.3.2 — Health check + Onboarding fix

Kullanıcı feedback: **"Ollama ve Qwen kurmak zorunda ama belirtilmiyor"**.

Bunun üzerine:
- `core/agent.check_ollama_health()` — başlangıçta Ollama'yı pingle
- Eksikse net Türkçe talimat: "brew install ollama && ollama pull qwen2.5:14b"
- README'ye prominent "Ön gereksinim" bölümü

### v0.3.3 — KRİTİK dev install fix

Smoke test sırasında garip bir bulgu: kullanıcı "İstanbul'da hava nasıl?"
sordu, model **"API anahtarı engellendi"** dedi (yalan! wttr.in API anahtarı
gerektirmez). Soruşturmada zincir:

```
1. Dev install (pip install -e .) → builtin_skills/ paket içinde yok
2. cwd != ajanox/ → cwd/skills bulamadı
3. 0 skill yüklendi → matcher boş katalog
4. system pseudo-skill → curl shell_unsafe → denied
5. Model gerçek sebebi söylemek yerine plausible bir YALAN üretti
```

Düzeltme: `_builtin_skills_dir()` için dev fallback — repo root'taki `skills/`
klasörü kullanılır. **Bu bug 1.5 saat sürdü ama 4 ayrı problem ortaya çıkardı:**
packaging, matching, security cascade, ve LLM halüsinasyonu.

---

## 8. v0.4.x — Skill Marketplace (14:00–18:00 UTC)

### v0.4.0 — `ajanox skill install <name>`

GitHub-tabanlı marketplace:

```bash
ajanox skill search                       # GitHub'dan 8 skill listele
ajanox skill install open-ports           # bare name (default registry)
ajanox skill install user/repo:foo        # shorthand
ajanox skill install https://github.com/x/y/tree/main/skills/foo  # tam URL
```

`core/registry.py` — Registry dataclass, URL parser, GitHub API integration,
yasak permission tespiti, manifest preview + onay.

**Default registry:** `yildirimozal/miniagent` — kullanıcının kendi başka
repo'su, 8 skill içeriyor (git-log, ip-location, json-format, open-ports vs.).

### v0.4.1 — KRİTİK web deadlock fix

Marketplace'ten `open-ports` yüklendi, tarayıcıdan denedi — modal görünüyor
ama "Evet" tıklasa bile **DENIED** dönüyordu. Soruşturma:

```
1. Agent thread approval beklerken (threading.Event.wait)
2. WS handler ws.receive_json() çağıramıyor (await edemiyor)
3. Client'ın approval_response mesajı 120s timeout'a kadar alınamıyor
4. Broker "no" döndürdü → DENIED
```

Klasik async/sync deadlock. Düzeltme: `stream_agent_events()` artık
`asyncio.create_task()` ile background'da, main loop `receive_json`'a hemen
geri döner.

**Ek (legacy mode):** `miniagent` skill'leri `permissions: []` (eski format).
Manifest yoksa default-deny yerine **runtime onay zorla** — her tool çağrısı
için kullanıcı görür modal. Marketplace ekosistemi 10x genişler.

### v0.4.2 — UI temizliği

Kullanıcı feedback: *"bir komuttan sonra gereksiz çıktılar veriyor, sadece
hızlıca son çıktıyı vermeli"*. UI artık:
- Sadece kullanıcı + Ajanox cevabı + güvenlik mesajları görünür
- Match/tool_call/tool_result event'leri "Detaylar (N adım) ▸" accordion'da
- Status bar'da current activity + canlı saniye sayacı

### v0.4.3 — Streaming + tool output görünür

Kullanıcı feedback: *"çıktının gelmesi de uzun sürüyor"*. 14B model Türkçe
sentezi 20-40 saniye sürüyor; ekran 30 saniye boyunca donmuş gibi görünüyordu.

Çözüm: **Token-by-token streaming**. `core/agent.chat_stream()` Ollama
`stream=true` ile, her token UI'a `assistant_chunk` event'i olarak gönderir.
Yanıp sönen `▍` cursor ile aktif streaming gösterilir.

**Sonuç:** Perceived latency 80% düşer. İlk kelimeler ~1-2 saniyede görünür,
ChatGPT/Claude pattern'i.

Aynı release: tool çıktısı (curl/lsof/du sonucu) artık mesaj listesinde
yeşil-kenarlı kompakt monospace kutuda görünür.

### v0.4.4 — VS Code tarzı skill kartları

Kullanıcı feedback: *"Skill isimleri tekrar ediyor. Ayrıca VS Code'daki gibi
temsili logolar olsa. Tıklanabilir olsun otomatik yürütülsün"*. Üçü birden:

1. **Dedup** — aynı skill name birden fazla kaynaktan gelirse panelde tek satır
2. **İkonlar** — skill manifest'inde `icon` alanı + fallback emoji map
   (🌤️ weather, 📂 find-large-files, 📊 system-info...)
3. **Tıklanabilir** — kart click → `example_prompt` otomatik gönderilir

5 builtin SKILL.md'ye `icon` + `example_prompt` eklendi.

---

## 9. v0.5.0 — Görsel Marketplace (gece geç saat)

Kullanıcı feedback: *"ajanox skill search → tarayıcıda görsel kart listesi
(install butonuyla)"*.

```
[Sidebar]
  🛒 Marketplace ← tıkla
       ↓
┌─────────────────────────────────────────────────┐
│  🛒 Skill Marketplace   8 skill  [Yenile] [×]  │
│  ┌────────────────────────────────────────────┐ │
│  │ 🔍 Skill ara… (live filter)                │ │
│  └────────────────────────────────────────────┘ │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │ 🌿      │  │ 📍      │  │ 📋      │         │
│  │ git-log │  │ ip-loc. │  │ json-f. │         │
│  │miniagent│  │miniagent│  │miniagent│         │
│  │ [Yükle] │  │ ✓ Yüklü │  │ [Yükle] │         │
│  │         │  │ [Kaldır]│  │         │         │
│  └─────────┘  └─────────┘  └─────────┘         │
└─────────────────────────────────────────────────┘
```

4 backend endpoint + 300 satır UI:
- `GET /api/marketplace/skills` (5 dk cache)
- `GET /api/marketplace/skill/{registry}/{name}` (manifest detayı)
- `POST /api/marketplace/install` (yasak permission → 403)
- `POST /api/marketplace/remove`

**Live search**, **install state senkron**, **yasak permission koruması**,
**auto-refresh** install sonrası sol skill paneli.

---

## 10. Bug'lar ve Dersler

Dürüst bölüm — yapılan hatalar, çözümler.

### Halüsinasyon (kullanıcı gerçek senaryoda yakaladı)

**Olay:** Web dashboard'da "İstanbul'da hava nasıl?" → model
"API anahtarı engellendi" diye yanıtladı.
**Gerçek sebep:** Dev install'da builtin_skills paket içinde değildi → 0
skill → curl denied → model **gerçek sebebi söylemek yerine yalan uydurdu**.

**Ders:** LLM'ler güvenlik denied senaryolarında "plausible" yalanlar üretir.
**Tool-call verification** (model "yaptım" derken gerçekten yapıldı mı?) v0.6'da
gelmeli.

### Web Deadlock

**Olay:** Modal görünüyor, "Evet" tıklanıyor, ama DENIED.
**Sebep:** Agent thread approval beklerken WS handler client mesajını
alamıyor. Klasik async/sync bridge bug'ı.
**Düzeltme:** `asyncio.create_task()` ile agent loop background'a.

### Disk Dolu

**Olay:** Mac SSD %100 doldu (120 MB kaldı). Edit'ler `ENOSPC` veriyor.
**Sebep:** Time Machine local snapshots + Ollama modelleri + macOS Library.
**Düzeltme:** `tmutil thinlocalsnapshots / 999999999999 4`, vs. → 4.5 GB
geri kazanıldı.
**Ders:** Local AI geliştirme disk yer tüketimi gerçek bir kısıt — kullanıcı
deneyiminin parçası.

### Coder Modeli Fos

Smoke test'te `qwen2.5-coder:7b` denedik, %0 başarı — JSON'u text olarak
yazıyor, Ollama parse etmiyor. **Ders:** Model + framework birleşimi her zaman
test edilmeli, hiçbir kombinasyon "çalışıyor olması beklenir" demez.

---

## 11. Sayılar

### Bugün yapılanlar

| | |
|---|---|
| **Release** | 12 (v0.2.0 → v0.5.0) |
| **GitHub commit** | 15+ |
| **GitHub tag** | 12 |
| **PyPI sürümü** | 6 (0.2.1, 0.3.1, 0.3.3, 0.4.0, 0.4.1, 0.5.0) |
| **Unit test** | 97/97 ✓ |
| **Smoke test** | 15/15 ✓ |
| **Toplam test geçen** | 112 |

### Kod

| Dil/dosya | Satır |
|---|---|
| Python (`src/ajanox/`) | ~2900 |
| HTML/CSS/JS (`web/static/`) | ~650 |
| Tests | ~1100 |
| Docs (markdown) | ~1500 |
| Built-in skills (SKILL.md) | ~250 |
| **Toplam** | **~6400** |

### Mimari

| | |
|---|---|
| **HTTP endpoint** | 6 (`/`, `/api/info`, `/api/marketplace/*`) |
| **WebSocket endpoint** | 1 (`/ws`, real-time event stream) |
| **CLI komut** | 7 (`ajanox`, `web`, `skill init/list/check/install/remove/search`) |
| **Built-in skill** | 5 (weather, find-large-files, system-info, mac-notification, delete-old-logs) |
| **Marketplace skill** (miniagent registry) | 8 |
| **Permission** | 14 (file_read, shell_safe, network_read, ..., sudo-yasak) |
| **Critical path** | 26 (~/.ssh, /etc, ~/Library, ...) |
| **Shell_safe whitelist** | 33 binary |
| **Dangerous flag tespiti** | 3 (find -delete, find -exec, sed -i) |

---

## 12. Açık Kalan

Bugün bitmedi — sadece bir başlangıç. Bilinen sınırlamalar:

| | Kabul | Çözüm planı |
|---|---|---|
| **Tool-call verification** | Model "yaptım" derken yalan söyleyebilir | v0.6 — tool output'u zorla kullan, yoksa reddet |
| **Streaming sadece web'de** | CLI hâlâ tam cevap bekliyor | v0.6 — CLI streaming |
| **Sandbox** | Opt-in (`AJANOX_SANDBOX=strict`) | v0.7 — default sandbox-exec/bwrap |
| **Multi-user / RBAC** | Tek kullanıcı varsayım | v1.0 |
| **Cross-platform** | macOS + Linux test edildi; Windows WSL2 yok | v0.6 |
| **Skill imzalama** | Yok | v1.0 (marketplace güvenliği için) |
| **Domain allowlist** | network_read tüm internet'e açık | v0.7 (`allowed_domains` manifest) |
| **Flag-level whitelist** | `sed -i` vs `sed -n` ayrımı limitli | v0.7 |

---

## 13. Vizyon — uzun yol

Mevcut konum: **L3** (Ubuntu/macOS üstüne paket).

```
v0.5.x (BUGÜN)  →  v1.0       →  v2.0           →  v3.0+
   L3                L3            L2                L2 + kernel
Ubuntu/macOS     Stabil API   Ubuntu remix     eBPF + LSM ile
üstüne paket    + topluluk    distro (Pop_OS    kernel-derinliği
                              modeli, kendi      policy enforcement
                              installer)
```

**Asla:** Sıfırdan kernel. Linus 35 yıl Linux'a verdi — biz o yolu
tekrarlamayız. Ajanox'un farkı kernel inovasyon değil, **AI ajan katmanı**.

---

## 14. Krediler & Stack

### Kim

- **Özal Yıldırım** ([@yildirimozal](https://github.com/yildirimozal)) — vizyon,
  mimari kararlar, kullanıcı testleri, ürün yönü, gerçek dünya feedback (bug
  yakalama içgüdüsü)
- **Claude Opus 4.7** (Anthropic) — kod, dokümantasyon, debug, refactor,
  her commit `Co-Authored-By:` ile imzalı

### Önceki çalışma

- **miniagent** ([yildirimozal/miniagent](https://github.com/yildirimozal/miniagent))
  — kullanıcının kendi minimum POC'u, Ajanox'un çekirdeği bunun üstüne
  inşa edildi. SKILL.md formatı buradan geldi.
- **OpenClaw** — lazy-load skill katalog pattern'i (skill description'lar
  sistem promptunda, body model çağırınca okunur)
- **Anthropic Claude Skills** (Eylül 2025) — markdown-based skill paradigması
- **Android permission model** — runtime onay UX'inin temeli

### Stack

| Katman | Teknoloji |
|---|---|
| **LLM runtime** | [Ollama](https://ollama.ai) v0.24 |
| **Model** | [Qwen 2.5 14B](https://qwen.ai) (Alibaba, Apache 2.0) — Türkçe + tool-calling odaklı |
| **Dil** | Python 3.10+ (stdlib + PyYAML tek prod bağımlılığı) |
| **Web** | FastAPI 0.136 + Vue 3 (CDN) + WebSocket |
| **Paketleme** | hatchling + twine + wheel |
| **CI/CD** | GitHub Actions (ubuntu + macos, Python 3.10/3.11/3.12) |
| **Lisans** | Apache 2.0 |

### Tetikleyici Trendler (2026 başı)

- **Privacy backlash** — kullanıcılar verisini cloud'a vermek istemiyor
  (Apple Intelligence "on-device" pazarlandı, ama kapalı)
- **Local LLM olgunlaşması** — Qwen 2.5 / Llama 3.x / Mistral consumer
  hardware'da çalışabiliyor
- **Agentic AI growth** — pure chat → agent + tool-use (2025 ana trend)
- **Türkiye'de AI ilgisi** — yerli alternatif arayışı (KVKK, devlet
  bağımsızlık vizyonu)

Ajanox bu kesişimde duruyor: **yerel + Türkçe + açık + güvenli ekosistem-merkezli
agentic OS katmanı.**

---

## 15. Tekrar Edilebilir mi?

**Evet.** Bu yolculuğun reçetesi:

1. **Net vizyon, açık mimari** — 4 katmanlı diyagram önce gelsin
2. **Doğru kısıtları seç** — yerel LLM, açık kaynak, Apache 2.0
3. **POC önce, polish sonra** — 14B + prompt-based hipotezi smoke test'le doğrula
4. **Kullanıcı feedback'ini cidden al** — "skill isimleri tekrar ediyor" 1 saat içinde fix'lendi
5. **Halüsinasyonu beklemediğin yerde ara** — "API anahtarı engellendi" bir bug zincirini açtı
6. **Versiyonla cesur ol** — 12 release/gün, her biri küçük + odaklı
7. **Commit mesajlarına yatır** — 6 ay sonra "niye buradayım" demem
8. **AI co-pilot'u stratejik kullan** — kod yazdırırken bile sen yöneticisin

---

## Bağlantılar

- 📦 **PyPI**: https://pypi.org/project/ajanox/
- 💻 **GitHub**: https://github.com/yildirimozal/ajanox
- 📋 **CHANGELOG**: [CHANGELOG.md](../CHANGELOG.md)
- 📜 **Skill Spec v0.1**: [SPEC.md](SPEC.md)
- 🛡️ **Security Model**: [SECURITY.md](SECURITY.md)
- 🏗️ **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- 👨‍💻 **Developer Guide**: [DEVELOPER.md](DEVELOPER.md)

---

> *"Boş bir klasör + bir vizyon + bir AI asistan + 24 saat = public bir
> agentic OS layer. Bu bir nedenden çok, bir mümkünlük."*
>
> — Ajanox, v0.5.0 — 2026-05-21
