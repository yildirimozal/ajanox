# APT / PPA packaging

Launchpad PPA: `ppa:yildirimozal/ajanox`. Modül E.

## Durum

Boş — Modül E (Ay 6) doldurulacak.

## Niçin

L2 ISO'su Ajanox'u önceden kurar — ama kullanıcı güncelleme alabilmeli.

```bash
sudo apt update
sudo apt upgrade ajanox-python
sudo apt upgrade ajanox-firstrun ajanox-gnome-extension
```

Tek mekanizma, version skew yok.

## İçerik (planlanan)

```
apt/
├── debian/                     # debian packaging
│   ├── control                 # paket meta + bağımlılıklar
│   ├── changelog               # versioning (dch -i ile)
│   ├── copyright               # lisanslar
│   ├── rules                   # build kuralları (debhelper)
│   ├── compat                  # debhelper level
│   ├── ajanox-python.install   # hangi dosyalar nereye
│   ├── ajanox-firstrun.install
│   └── ajanox-gnome-extension.install
├── recipes/                    # Launchpad recipe (auto-build)
│   └── ajanox-noble.recipe
└── README.md
```

## Build

```bash
# Local test
cd apt
dpkg-buildpackage -us -uc -b
ls ../*.deb
sudo dpkg -i ../ajanox-python_*.deb
```

## Launchpad'e push

```bash
# Bir kerelik:
ssh-keygen -t ed25519 -C "launchpad"
# Public key Launchpad → SSH Keys
gpg --gen-key
# Public key Launchpad → OpenPGP Keys

# Her release'de:
dch -i  # changelog'a yeni entry
dpkg-buildpackage -S -sa  # source package
dput ppa:yildirimozal/ajanox ../ajanox-python_*_source.changes
```

Launchpad otomatik build eder (~10-30 dk).

## Recipe (CI alternatifi)

Launchpad recipe → her commit'te auto-build, daily PPA güncellemesi:

```
# ajanox-noble.recipe
# bzr-builder format 0.4 deb-version {debversion}+{revno}
lp:~yildirimozal/ajanox/main
```

## v2.0 base PPA

L2 ISO'su default şu PPA'ları aktive eder:

```bash
# /etc/apt/sources.list.d/ajanox.list
deb https://ppa.launchpadcontent.net/yildirimozal/ajanox/ubuntu noble main
deb https://ppa.launchpadcontent.net/yildirimozal/ajanox-skills/ubuntu noble main
```

İkinci PPA topluluk skill'leri için (Modül F + marketplace).

## Paket isimleri

| Paket | Ne |
|---|---|
| `ajanox-python` | L3 Python core (PyPI'dan değil, .deb'lenmiş) |
| `ajanox-firstrun` | İlk açılış wizard |
| `ajanox-gnome-extension` | GNOME Shell extension |
| `ajanox-branding` | Logo, wallpaper, tema |
| `ajanox-skills-default` | Sistem skill paketi (Modül F) |
| `ajanox-meta` | Hepsini çeken meta package (`apt install ajanox`) |
