# Katkı

Ajanox L2 projesi henüz **erken faz** (v2.0 geliştirme). Public PR/issue
şu an sınırlı; v2.0 alpha'ya kadar issue tracker yalnızca planlama notu
ve mimari tartışmaya açık.

## Bu repo nereye odaklanır

- ISO build pipeline (`iso/`)
- First-boot wizard (`firstrun/`)
- GNOME Shell extension (`gnome-extension/`)
- APT packaging (`apt/`)
- Branding asset'leri (`branding/`)
- Acceptance test'leri (`tests/`)

## L3 (ajanox Python paketi) işleri buraya değil

- Yeni skill ekleme → [yildirimozal/ajanox](https://github.com/yildirimozal/ajanox)
- L3 paketinde bug → [ajanox issues](https://github.com/yildirimozal/ajanox/issues)
- Skill spec değişikliği → ajanox repo'sunda RFC

## Issue açmadan önce

L2 v2.0 stable olana kadar:

1. **Wi-Fi/donanım sürücüsü** → bu Ubuntu base'in sorumluluğu, ajanox-l2'de
   sadece pre-config var. Ubuntu issue tracker'ına yönlendiririz.
2. **ISO çalışmıyor** → minimum `inxi -Fxz` çıktısı + `dmesg` log ekle
3. **Firstrun crash** → `~/.config/ajanox/firstrun.log` ekle

## Geliştirme

Dev loop için [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

ISO build için [docs/BUILDING.md](docs/BUILDING.md).

## Lisans

Apache 2.0 (kod). Branding asset'leri için CC-BY-SA 4.0 (`branding/`).

Katkı yaparken her dosyanın lisansı altında olduğunu kabul edersin.
