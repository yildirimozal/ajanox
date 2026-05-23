# Roadmap

## v2.0 — Ubuntu Remix (hedef: 10 ay solo)

| Ay | Milestone | Çıktı |
|---|---|---|
| 1-2 | Modül A — ISO build pipeline (Cubic) | İlk bootable ISO |
| 3 | Modül B — First-boot wizard | Türkçe GTK wizard |
| 4 | Modül C — GNOME Shell extension | Top bar tray + Cmd+Space |
| 5 | Modül D — Brand identity | Logo, wallpaper, GRUB tema |
| 6 | Modül E + F — APT/PPA + sistem skill paketi | PPA'dan apt install |
| 7 | Alpha (kapalı, 10-20 tester) | Donanım uyumluluk raporu |
| 8 | Beta (public, GitHub Releases) | Genel kullanım, issue toplama |
| 9 | Bug fix + polish | RC1, RC2 |
| 10 | v2.0 stable release | DistroWatch entry, basın launch'u |

## v2.1 (kapsam: ~3 ay)

- live-build + Packer ile CI'dan otomatik ISO
- ARM64 base paralel
- Türkiye mirror'ları (ULAKBIM, üniversiteler)
- 5+ ek sistem skill'i (wifi-manage, bluetooth-pair, vpn-connect)

## v3.0 (kapsam: 6+ ay, L2'den sonra)

eBPF + LSM ile sistem-genişi enforcement. Ayrı RFC dokümanı gerekir.
Detay: [ajanox/docs/roadmap-v2-v3.md](https://github.com/yildirimozal/ajanox/blob/main/docs/roadmap-v2-v3.md)

## v2.0 başlangıç ön koşulları

L3 tarafında **bunlar bitmeden L2 başlanmaz:**

- [ ] `ajanox` v1.0 release (API freeze)
- [ ] Tool-call verification (halüsinasyon koruma) — `ajanox` v0.6
- [ ] Sandbox default-on (bwrap, sandbox-exec) — `ajanox` v0.7
- [ ] Cross-platform smoke test — `ajanox` v0.8
- [ ] Domain allowlist + skill imzalama — `ajanox` v0.9

L3 v1.0'a ulaşmadan L2'de yapılan iş "throwaway" risk taşır.

## Karar noktaları (henüz cevaplanmadı)

| Karar | Seçenekler | Notlar |
|---|---|---|
| Base distro | Ubuntu, Debian, Fedora | Ubuntu 24.04 LTS (driver, Ollama desteği) |
| Desktop env | GNOME, KDE, Cinnamon | GNOME (Türkçe + default) |
| Default browser | Firefox, Chromium | Firefox (Türkçe + privacy) |
| Default editor | VS Code, Vim, GNOME Text | VS Code (developer hedefli) |
| Default terminal | GNOME Terminal, Wezterm | Wezterm (modern, tema'lanabilir) |
| ISO host | GitHub Releases, B2, BitTorrent | LFS limit, mirror gerekir |
| Lisans (branding) | Apache vs CC-BY-SA | Logo/asset için ayrı |

## Bağımlılıklar

- **Designer:** Logo + wallpaper için freelance (~1500-3000 USD bütçe)
- **Lab donanım:** 1 NUC/mini-PC + Ventoy USB (~5-8 bin TL)
- **Alpha tester havuzu:** 10-20 kişi (topluluk çağrısı)
- **Mirror anlaşmaları:** ULAKBIM, üniversiteler (TÜBİTAK ile görüş)
