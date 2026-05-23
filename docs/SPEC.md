# Ajanox Skill Specification v1.0

> **Durum:** v1.0 DONMUŞ (2026-05-23). Ajanox 1.0.0 ile birlikte Skill Spec
> kararlı kabul edilir. **1.x serisi boyunca breaking change YOK** — yalnız
> geriye uyumlu ekleme (yeni opsiyonel alanlar, yeni permission'lar). Kırıcı
> değişiklikler 2.0'a saklanır.
> **Spec'in kendi sürümü:** 1.0.0 (semver)
> **Uyum garantisi:** `ajanox: ">=1.0.0 <2.0.0"` belirten bir skill 1.x'in
> sonuna kadar çalışır. Sürüm uyumu `ajanox skill` katalog yüklemede otomatik
> kontrol edilir (`core/compat.py`); uyumsuz skill'ler uyarıyla atlanır.
> v0.x manifest'leri `ajanox skill migrate <dir>` ile 1.x'e yükseltilir.

---

## 1. Niye bir spec?

Skill = Ajanox'un **yeteneklerini genişletme birimi** ve aynı zamanda **üçüncü taraf entegrasyon noktası**. Bu yüzden:

- Geliştiriciler buna göre yazacak → değişmek pahalı
- Otomasyonlar (CLI, marketplace, IDE eklentileri) bunu parse edecek
- Güvenlik denetimi bu manifest'i okuyacak
- Versioning + dependency çözümü bu metadata'ya dayanacak

Spec'in dört temel **prensibi**:

1. **Markdown-first** — geliştirici bir kod editöründe yazabilsin, Python öğrenmesin
2. **Frontmatter manifest, body talimat** — makine + insan ayrılığı
3. **Açık izinler (explicit permissions)** — skill ne yapacağını **önceden** beyan eder, kullanıcı onaylar
4. **Geriye dönük uyum garantili** — `ajanox: ">=1.0"` belirten bir skill, 1.x serisinin sonuna kadar çalışmalı

---

## 2. Dizin Yapısı

```
skills/
├── <skill-name>/                    ← kebab-case, alfanumerik + tire
│   ├── SKILL.md                     ← ZORUNLU — manifest + talimat
│   ├── examples/                    ← OPSİYONEL — örnek girdi/çıktı (test için)
│   │   ├── basic.input.txt
│   │   └── basic.expected.txt
│   ├── assets/                      ← OPSİYONEL — ikon, resim, ek dosyalar
│   │   └── icon.svg
│   └── lib/                         ← OPSİYONEL — yardımcı script'ler (skill body'sinden çağrılır)
│       └── helper.sh
```

**Karar (A — kapatıldı):** `lib/` altında script çalıştırma izinli, ama **`permissions: [lib_execute]` zorunlu beyan**. Skill'in `lib/helper.sh`, `lib/script.py` gibi yardımcıları olabilir; runtime onlara `lib_execute` izniyle bash veya python ile erişir. Güç ↔ güvenlik dengesi için bu kontrol şart.

---

## 3. Manifest (Frontmatter) Şeması

`SKILL.md` dosyasının başında YAML frontmatter:

```yaml
---
# === Zorunlu alanlar ===
name: find-large-files               # kebab-case, dizin adıyla aynı, globally unique
version: 1.2.0                       # semver — skill'in kendi sürümü
description: >                       # 1 cümle, hangi durumda kullanılır (LLM bunu görür)
  Bir klasördeki en büyük dosyaları ve alt klasörleri listeler.

ajanox: ">=0.1.0 <1.0.0"             # uyumlu Ajanox sürüm aralığı (semver range)

permissions:                         # ZORUNLU — boş [] olabilir, yok edilemez
  - shell_safe                       # tehlikesiz shell komutları (read-only sayılan)
  - file_read

# === Önerilen alanlar ===
author:
  name: Özal Yıldırım
  email: ozal@example.com            # opsiyonel
  github: yildirimozal               # opsiyonel

license: Apache-2.0                  # SPDX identifier
homepage: https://github.com/yildirimozal/ajanox-skills/find-large-files

tags: [filesystem, disk-usage, cleanup]
language: tr                         # skill talimat dilinin BCP-47 kodu (tr, en, de…)
languages: [tr, en]                  # birden fazla dil destekleniyorsa

# === Opsiyonel alanlar ===
dependencies:                        # diğer skill'lere bağımlılık (semver)
  - name: confirm-prompt
    version: ">=0.1.0"

requires:                            # sistem-seviyesi bağımlılık (binary, OS)
  binaries: [du, sort, head]
  os: [linux, darwin]                # bu skill hangi OS'larda çalışır
  internet: false                    # internet erişimi gerekir mi

# === Marketplace alanları (ileride) ===
icon: assets/icon.svg                # opsiyonel
screenshots: [assets/demo.png]       # opsiyonel
keywords: [disk, temizlik, ...]      # arama için
---
```

### Permission seti (B1 — kapatıldı)

Android'in app permissions modeline yakın. v0.1'in kapanmış permission listesi:

| Permission | Anlam | Risk seviyesi | Onay zamanı |
|---|---|---|---|
| `file_read` | Dosya okuma (sistem path'leri dahil; sudo gerekli olanlar ayrıca `sudo` ister) | Düşük | install |
| `file_write` | Dosya yazma/silme/değiştirme | **Yüksek** | **runtime** |
| `shell_safe` | Whitelist'teki read-only komutlar (`ls`, `du`, `cat`, `ps`, `df`, …). Whitelist Ajanox core tarafından yönetilir. | Düşük | install |
| `shell_unsafe` | Keyfi shell komutu | **Yüksek** | **runtime** |
| `network_read` | HTTP GET, ping (read-only) | Orta | install |
| `network_write` | POST, PUT, file upload, webhook | **Yüksek** | **runtime** |
| `process_read` | Process listesi, info | Düşük | install |
| `process_control` | Kill, signal | **Yüksek** | **runtime** |
| `system_info` | OS, CPU, RAM bilgisi | Düşük | install |
| `notification` | Sistem bildirimi gönderme | Düşük | install |
| `audio_play` | Ses çıkışı (TTS, alarm vs.) | Düşük | install |
| `clipboard` | Pano okuma/yazma | Orta | install |
| `lib_execute` | Skill'in kendi `lib/` altındaki script'lerini çalıştırma | Orta | install |
| `sudo` | Yetki yükseltme | **Kritik** | **runtime, her komutta** |

**Whitelist yönetimi:** `shell_safe` whitelist'i Ajanox core repo'da `core/whitelist.yml` olarak tutulur. Yeni komut eklemek minor version bump gerektirir. Üçüncü taraflar değiştiremez.

### Onay modeli (B2 — kapatıldı): Hibrit (Android "dangerous permissions")

**Install'da:**
- Kullanıcı skill yüklerken full permission listesini görür → onaylar → skill kurulur.
- Manifest'teki tüm permission'lar listede.

**Çalışma zamanında:**
- **Düşük/orta risk** permission'lar (install'da onaylananlar): runtime'da sessizce çalışır, ek soru sorulmaz.
- **Yüksek risk** permission'lar (tabloda kalın olanlar): her çağrıda **runtime onayı**. Örnek prompt:
  > Skill `delete-old-logs` şu komutu çalıştırmak istiyor:
  > `rm -f /Users/ozal/logs/old.log /Users/ozal/logs/older.log`
  > İzin? [E/H/T (tümünü reddet)]
- **Kritik (`sudo`)** her seferinde, başka onay seçeneği yok.

Bu Android'in başarılı UX'i: sessiz çalışma + tehlikeli aksiyon görünürlüğü.

### Permission spec evrimi (B3 — kapatıldı)

- **Yeni permission eklemek:** breaking değil. Eski skill'ler yeni runtime'da çalışmaya devam eder.
- **Permission kaldırmak / yeniden adlandırmak:** major version bump (örn. v1 → v2).
- **Permission'ın risk seviyesini değiştirmek** (örn. düşük → yüksek): minor version bump + bütün marketplace skill'lerinde yeniden onay ister.

---

## 4. Versioning ve Uyumluluk

- **Skill version** semver: `MAJOR.MINOR.PATCH`
- **Spec version** (`ajanox` alanı): semver range; örn `">=0.1.0 <1.0.0"`
- 1.0 yayınlanana kadar 0.x'lerde **kırıcı değişiklik özgürlüğü** var; 1.0 sonrası major bump zorunlu
- Marketplace skill'leri otomatik uyum kontrolünden geçer (`ajanox` range uyumlu mu)

**Karar (C — kapatıldı):** Tek skill, tek sürüm. Node `node_modules` multi-version karmaşıklığı %90 gereksiz. Geliştirici farklı bir sürüm test etmek istiyorsa farklı bir skill ismi kullansın (örn. `weather` → `weather-next`). v2.0'da gerçek bir kullanım durumu çıkarsa multi-version eklenebilir.

---

## 5. Body (Talimat İçeriği)

Frontmatter'dan sonra Markdown talimatları. **Öneri yapı** (zorunlu değil ama önerilen):

```markdown
# <Skill Title>

## Kısa açıklama
[1-2 paragraf, ne işe yarar]

## Kullanım durumu
[Hangi tip kullanıcı sorgularına yanıt verir]

## Parametreler (eğer varsa)
- `klasor` (zorunlu): aranacak yol, örn `~/Downloads`

## Çalıştırılacak komut
```bash
du -ah <klasor> 2>/dev/null | sort -hr | head -10
```

## Sonuç işleme
[Çıktıyı kullanıcıya nasıl sun, neyi vurgula]

## Hata durumları
- Klasör yoksa: "Klasör bulunamadı: <yol>" şeklinde bildir
- İzin yoksa: sudo isteme, sadece raporla
```

**Karar (D — kapatıldı):** Sadece öneri, zorunlu değil. Markdown gücü esnekliktedir. `ajanox skill check` linter komutu önerilen yapıyla uyumu rapor eder ama hata vermez. Body LLM'in göreceği metin — geliştirici en iyi bildiği şekilde yazmakta serbest.

---

## 6. miniagent Geriye Uyumluluğu

miniagent v2 SKILL.md'leri minimum manifest (`name`, `description`) kullanıyor. Ajanox v0.1'de:

- `version` defaulta `0.0.0`
- `permissions` defaulta `[shell_unsafe]` (geriye uyumlu ama UYARI verilir)
- `ajanox` defaulta `*` (yine UYARI)
- Mevcut miniagent skill'leri çalışır, ama yükleyicide "v0.x SKILL.md, lütfen upgrade edin" uyarısı

**Karar (E — kapatıldı):** v0.x boyunca geriye uyum + uyarı. v1.0'da temiz kesme. Migration için `ajanox skill migrate` komutu manifest'i otomatik upgrade eder (eksik alanları default'larla doldurur, öneri başlıkları ekler, vs.). v1.0'dan önce ekosistemdeki tüm skill'ler bu komutla yükseltilebilir.

---

## 7. Canonical Örnek: weather skill (v0.1 ile)

```markdown
---
name: weather
version: 0.1.0
description: Bir şehrin güncel hava durumunu söyler.
ajanox: ">=0.1.0 <1.0.0"
permissions: [shell_safe, network_read]
author:
  name: Özal Yıldırım
  github: yildirimozal
license: Apache-2.0
language: tr
requires:
  binaries: [curl]
  internet: true
tags: [weather, info]
---

# Weather Skill

Bir şehrin anlık hava durumunu wttr.in servisinden alır. API anahtarı gerekmez.

## Parametreler
- `sehir` (zorunlu): şehir adı, Türkçe karakterler İngilizce'ye çevrilmeli (İstanbul → Istanbul)

## Çalıştırılacak komut
```bash
curl -s 'https://wttr.in/<sehir>?format=3'
```

## Sonuç işleme
Çıktı tek satır gelir, örn: `Istanbul: 🌦 +16°C`. Kullanıcıya akıcı Türkçe ile aktar.

## Hata durumları
- Boş çıktı: "Hava durumu alınamadı, internet bağlantınızı kontrol edin."
- 404: "Şehir bulunamadı: <sehir>"
```

---

## 8. Kapatılan Kararlar (2026-05-20'de sonlandırıldı)

| # | Konu | Karar |
|---|---|---|
| A | `lib/` altında script izni | İzinli, `lib_execute` permission'ı ile |
| B1 | Permission seti | 14 permission (yukarıdaki tablo); `lib_execute`, `audio_play` eklendi; `file_read_system` birleştirildi |
| B2 | Onay zamanı | Hibrit: install (düşük/orta risk) + runtime (yüksek risk, her seferinde) |
| B3 | Permission evrimi | Ekleme breaking değil; kaldırma/risk-değişikliği major bump |
| C | Multi-version | Yok — tek skill tek sürüm (v0.1'de). v2.0'da yeniden değerlendirilir. |
| D | Body zorunlu yapı | Sadece öneri. Linter raporlar, hata vermez. |
| E | Geriye uyum süresi | v0.x boyunca uyarıyla; v1.0'da kırılma. Migration komutu sağlanır. |

---

## 9. Sıradaki adımlar

1. ✅ Açık kararları (A-E) tartış, karara bağla — **TAMAMLANDI**
2. Spec'i ana Ajanox repoya kopyala (`docs/SPEC.md`) — proje iskeleti kurulurken
3. İngilizce'ye çevir (`docs/SPEC.en.md`)
4. miniagent kodunu Ajanox `core/` altına taşı, bu spec'e göre yenile
5. JSON Schema yaz (`schemas/skill-manifest.v0.1.json`) — otomatik validation için
6. `ajanox skill init` CLI komutu — bu spec'e uygun boilerplate üretir
7. `ajanox skill check` linter — body önerilerine uyumu rapor eder
8. `ajanox skill migrate` — v0.x → v1.0 manifest yükseltme
