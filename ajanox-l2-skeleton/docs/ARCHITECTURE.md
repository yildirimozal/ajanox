# Mimari

## L2 ne demek?

Ajanox'un katman spektrumunda:

- **L3** (yapıldı) — pip ile kurulan paket; mevcut OS üstüne biner
- **L2** (bu repo) — Ubuntu fork, kendi ISO, kendi installer, default Ajanox shell
- L1 — kernel fork (yapılmayacak)
- L0 — sıfırdan kernel (yapılmayacak)

L2 = **Pop_OS modeli**. Ubuntu 24.04 LTS base + Ajanox custom layer = bağımsız
dağıtım. Kullanıcı ISO indirir, boot eder, ilk komutunu yazar.

## Niçin ayrı repo (`ajanox-l2`)

`ajanox` (L3) ile birleşik tek repo *mümkündü* ama üç sertlik var:

**1. CI ağırlığı.** Live-build veya Packer ile ISO build 30-40 dakika, ~12 GB
artifact üretir. L3 Python testleri 30 saniyede biter. Aynı repo = CI hijyeni
bozulur, GitHub Actions storage limiti dolar.

**2. Release tempoları farklı.** L3 → PyPI'a 2-4 haftada bir. L2 → ISO 3-6
ayda bir. Tek tag space karışır.

**3. Issue/PR triyajı.** "Wi-Fi sürücüsü kırıldı" ve "Türkçe regex bug'ı"
aynı tracker'da boğulur. Mac kullanıcısı L2 repo'sunu hiç görmek zorunda
değil.

Üstüne dosya tipi şizofrenisi: PyGObject GTK + TypeScript GNOME extension +
Cubic config + debian/ + branding PNG + GRUB tema — bunların hiçbiri Python
core'la birlikte yaşamamalı.

## L3'le ilişki

L2 ISO'su belirli bir L3 paket versiyonunu **pinli** çeker:

```
# apt/debian/control
Depends:
 python3-pip,
 ollama (>= 0.4.0),
 ajanox-python (= 1.0.2),
 ...
```

**Sözleşme:** L2 sadece `ajanox` v1.0+ ile çalışır (API freeze sonrası). v1.0
öncesinde ISO build kararsız, üretime gönderilmez.

## Yapı taşları (modüller)

| Modül | Dizin | Tahmin |
|---|---|---|
| A — Custom ISO | `iso/` | 2 ay |
| B — First-boot wizard | `firstrun/` | 2 hafta |
| C — GNOME Shell extension | `gnome-extension/` | 4 hafta |
| D — Branding | `branding/` | 2 hafta (designer paralel) |
| E — APT/PPA | `apt/` | 1 hafta |
| F — Sistem skill paketi | (L3'te) | 3 hafta |

Modül F skill'leri L3 repo'sunda yaşar; L2 ISO'su onları default install eder.

## Cross-repo dependency

L3 → L2 yön yok. L2 → L3 var (apt depends). Kırılma noktaları:

- L3'te breaking API change → L2 ISO build kırılır → version pin yardımcı
- L3 skill API değişikliği → installed skill'ler bozulur → semver disiplini

**Çözüm:** `ajanox-l2/ci/integration.yml` daily olarak son L3 stable +
mevcut L2 config'ini smoke test eder. Kırılırsa issue açar.
