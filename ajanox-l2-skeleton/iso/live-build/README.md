# live-build ISO (v2.1+)

CI'da otomatik ISO build. v2.0'da Cubic ile prototip kanıtlandıktan sonra
buraya geçilir.

## Durum

Boş — v2.1'de doldurulacak. v2.0'da elle Cubic kullan.

## İçerik (planlanan)

```
live-build/
├── auto/
│   ├── config              # lb config çağrıları
│   └── build               # lb build wrapper
├── config/
│   ├── package-lists/      # hangi paketler yüklensin
│   ├── hooks/              # chroot ve binary hook'lar
│   ├── includes.chroot/    # chroot içine kopyalanacak dosyalar
│   └── preseed/            # otomatik installer cevap dosyaları
└── README.md
```

## Niçin Cubic değil

Cubic GUI — solo dev'in ilk ISO'sunu hızla çıkarması için iyi. Ama:

- CI'da çalışmaz (headless)
- Reproducible değil (manuel click'ler)
- Diff/review yok (chroot içi değişiklikler track edilmez)

live-build her şeyi config dosyalarına yazar — git'lenebilir, review'lanabilir,
CI'da çalıştırılabilir.

## Kullanım

```bash
cd iso/live-build
sudo lb build  # ~30-40 dk
```

Detay: [docs/BUILDING.md](../../docs/BUILDING.md) bölüm "live-build ile".
