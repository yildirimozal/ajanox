# Branding

Logo, wallpaper, GRUB tema, GNOME shell theme. Modül D.

## Durum

Boş — Modül D (Ay 5, designer ile paralel) doldurulacak.

## İçerik (planlanan)

```
branding/
├── logo/
│   ├── ajanox-logo.svg         # master, scalable
│   ├── ajanox-logo-mark.svg    # sadece sembol (favicon)
│   ├── ajanox-logo-light.png   # light bg için
│   ├── ajanox-logo-dark.png    # dark bg için
│   └── exports/                # 16/32/64/128/256/512 PNG
├── wallpapers/
│   ├── ajanox-day.png          # 3840x2160
│   ├── ajanox-night.png
│   ├── ajanox-abstract-1.png
│   ├── ajanox-abstract-2.png
│   └── ajanox-abstract-3.png
├── grub-theme/
│   ├── theme.txt
│   ├── background.png
│   └── icons/
├── gnome-shell-theme/
│   ├── gnome-shell.css
│   └── assets/
├── plymouth-theme/             # boot splash
│   ├── ajanox.plymouth
│   └── ajanox.script
└── README.md
```

## Tasarım kararları

| Eleman | Karar |
|---|---|
| Primary color | Ajanox blue `#7c9eff` |
| Accent | Yeşil (skill çalıştırma) + Kırmızı (güvenlik onayı) |
| Tipografi | Inter (sistem), JetBrains Mono (terminal) |
| Logo stili | Minimal, akılda kalıcı, scalable |
| Wallpaper | Türkiye coğrafyası refs? Veya soyut + AI temalı? |

## Designer süreci

**Bütçe:** 1500-3000 USD (freelance, Behance/Dribbble).

**Brief:**

- Yerel-first, açık kaynak, Türkçe-first agentic OS
- Hedef kitle: geliştiriciler + meraklı kullanıcılar (18-45)
- Pop_OS, Elementary OS, Ubuntu görsel dilini referans al
- Türk motifleri **opsiyonel** — zorlanmasın

**Çıktılar:**

1. 3 logo konsepti → 1 seçili → final variants
2. 5 wallpaper (gündüz/gece/abstract×3)
3. GRUB + Plymouth + GNOME shell tema'sı (logo'dan türetilen)
4. Sticker/T-shirt mockup (topluluk için)

## Lisans

Branding asset'leri **CC-BY-SA 4.0** (kod Apache 2.0'dan ayrı). Sebep:
"Ajanox" markası altında resmi olmayan dağıtım yapılmaması için.

`branding/LICENSE.md` ayrı dosya, designer kontratında belirt.

## .gitkeep notu

Klasörler şu an `.gitkeep` ile boş. Asset'ler eklenince `.gitkeep` silinir.
Büyük PNG'ler için `.gitignore` zaten exclude ediyor — LFS düşün (>5 MB):

```bash
git lfs track "branding/wallpapers/*.png"
```
