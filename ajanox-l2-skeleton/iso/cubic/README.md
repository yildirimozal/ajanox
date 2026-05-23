# Cubic ISO build (v2.0 prototip)

GUI tabanlı, hızlı iterasyon için. v2.0'ın ilk ISO'ları buradan çıkar.

## Durum

Boş — Modül A başlangıcında doldurulacak.

## İçerik (planlanan)

```
cubic/
├── build-v2.0/              # Cubic working directory (gitignored)
├── chroot-scripts/          # chroot içinde çalışacak setup scriptleri
│   ├── 01-base.sh           # apt update, temel paketler
│   ├── 02-ollama.sh         # Ollama kurulum + qwen2.5 model
│   ├── 03-ajanox.sh         # pip install ajanox + default skill'ler
│   ├── 04-gnome.sh          # GNOME extension + Cmd+Space hotkey
│   └── 05-branding.sh       # wallpaper, GRUB, login splash
├── firstrun-files/          # /etc/skel'e kopyalanacak dosyalar
└── README.md
```

## Kullanım

[docs/BUILDING.md](../../docs/BUILDING.md) bölüm "Cubic ile (v2.0)".

## Notlar

- `build-v2.0/` git'lenmez (~12 GB)
- chroot scripts deterministic olmalı — aynı script ikinci sefer hata vermemeli
- Model indirme cache'lensin — her build 9 GB indirmek deli
