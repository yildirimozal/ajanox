# Ajanox L2 — Ubuntu Remix

> **Ajanox'un işletim sistemi katmanı.** Ubuntu 24.04 LTS tabanlı, kendi ISO'su,
> default Ajanox shell, gömülü Ollama + qwen2.5 modeli.
>
> L3 paketinin (PyPI) tamamlayıcısı — `pip install ajanox` ile kurulan agentic
> OS katmanını "indir-boot-kullan" haline getirir.

**İlgili repo:** [yildirimozal/ajanox](https://github.com/yildirimozal/ajanox) — L3 paketi (Python, PyPI)

---

## Durum

**v2.0 geliştirme aşaması** — henüz alpha değil.

L3 paketi (`ajanox`) v1.0'a (API freeze) ulaşana kadar L2 ISO'larında kararsız
davranış beklenir. v1.0 öncesi: deneysel build'ler, dağıtım yok.

## Mimari özet

| Katman | Ne | Repo |
|---|---|---|
| **L3** | Mevcut OS üstüne Python paketi | [ajanox](https://github.com/yildirimozal/ajanox) |
| **L2** | Ubuntu 24.04 fork, ISO + installer | **bu repo** |
| L1 | Kernel fork | yok (planlanmıyor) |
| L0 | Sıfırdan kernel | yok (planlanmıyor) |

**Niçin ayrı repo?** → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Hedef

- **Friction sıfır kurulum** — ISO indir, boot et, Ajanox çalışıyor. Ollama
  + 14B model dahil. Manuel `ollama pull` yok.
- **Sistem-derinliği skill'ler** — `system-update`, `wifi-manage`, `vpn-connect`
  gibi sudo gerektiren skill'ler L2'de güvenle çalışır (installer polkit
  ve AppArmor profillerini ön-yapılandırır).
- **GNOME Shell entegrasyonu** — Top bar Ajanox tray, `Cmd+Space` global
  hotkey, default Wezterm + VS Code + Firefox.
- **Türkçe-first** — Default dil Türkçe, İngilizce ikinci.

## Yapı

```
iso/                  ISO build configs (Cubic erken, live-build sonra)
firstrun/             İlk açılış sihirbazı (PyGObject GTK)
gnome-extension/      GNOME Shell extension (TypeScript)
branding/             Logo, wallpaper, GRUB, GNOME tema
apt/                  Debian packaging, PPA recipe
tests/                ISO acceptance testleri (QEMU smoke)
docs/                 Mimari, build, dev rehberi
```

Her klasörün içinde modül-özel README var.

## Hızlı bağlantılar

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Niçin L2, niçin ayrı repo
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — VM-based dev loop
- [docs/BUILDING.md](docs/BUILDING.md) — ISO build adımları
- [docs/ROADMAP.md](docs/ROADMAP.md) — v2.0 milestone planı

## Lisans

Apache License 2.0. Branding asset'leri için [branding/README.md](branding/README.md).
