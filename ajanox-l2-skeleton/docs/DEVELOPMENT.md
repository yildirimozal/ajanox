# Geliştirme

L2 dev loop L3'ten radikal farklı. **Üç ayrı döngü kur, her birini ayrı tut.**

## İç döngü: saniye–dakika (kod yaz, çalıştır)

ISO build'e bulaşma. Standart Ubuntu 24.04 VM'i bir kez kur, içine ajanox'u
dev mode'da bağla.

**Kurulum (tek seferlik):**

```bash
# Host'ta: VM kur — UTM (Mac), virt-manager/QEMU (Linux)
# Ubuntu 24.04 Server + GNOME minimal, 8 GB RAM, 30 GB disk
# SSH'i aktif et, snapshot al ("fresh")

# VM içinde:
git clone https://github.com/yildirimozal/ajanox
cd ajanox && pip install -e '.[web]'
sudo apt install ollama-cli
ollama pull qwen2.5:14b
```

**Her gün:**

```bash
# Host'ta VS Code Remote-SSH ile VM'e bağlan → localde çalışır gibi
# Kod kaydet → VM'de:
ajanox
```

VS Code Remote-SSH eklentisi → VM doğrudan editor'da, save → anında çalışır.
**Zamanın %80'i burada geçecek.** L3 dev hızıyla aynı.

## Orta döngü: 10-15 dakika (sistem entegrasyonu)

Firstrun wizard, GNOME extension, sudo skill'leri, tray icon. ISO yok ama
sistem state değişiyor.

**VM snapshot disiplini kritik:**

```bash
# Temiz Ubuntu + ajanox kurulu, ilk açılış öncesi → "fresh" snapshot
# Her firstrun testi öncesi:
virsh snapshot-revert ajanox-dev fresh
virsh start ajanox-dev
# wizard tetiklenir → bakıp döndür
```

**GNOME extension için:**

```bash
# Build, zip'le, VM'e at
cd gnome-extension && npm run build
scp dist/ajanox@yildirimozal.com.zip ajanox-dev:~

# VM içinde install + reload
gnome-extensions install ajanox@yildirimozal.com.zip
# X11'de: Alt+F2 → "r" → reload
# Wayland'de: nested gnome-shell
dbus-run-session -- gnome-shell --nested --wayland
```

Wayland reload sorunu yüzünden dev sırasında X11 session öneririz (release
öncesi Wayland'de tekrar test).

## Dış döngü: 30-60 dakika (fresh install acceptance)

Sadece release-candidate öncesi. ISO build + temiz VM'de installer'dan boot.

**v2.0 (Cubic ile prototip):**

1. Cubic GUI'de chroot değişikliği yap
2. Generate → ~10-15 dk → `ajanox-2.0.iso`
3. UTM/QEMU'da yeni VM aç, ISO'dan boot et
4. Installer çalış, firstrun başlat, test

Manuel ama doğru — solo dev için yeterli.

**v2.1+ (live-build + CI):**

Push'ta otomatik ISO. `iso/live-build/` altında config + `.github/workflows/iso.yml`.

## Donanım test (ayrı problem)

VM'de Wi-Fi/Bluetooth/GPU sürücüleri test edilemez.

**Solo bütçe:**

- 1 adet ucuz NUC/mini-PC (~5-8 bin TL) — bare-metal lab makinen
- 1 adet Ventoy USB stick — ISO at, herhangi makineye boot et
- 3-5 farklı laptop modelinde "boot edebiliyor mu" testi (arkadaş çevresi)

**Topluluk leverage:**

- Alpha programı 10-20 tester — kendi donanımlarında test eder
- Issue template'inde `inxi -Fxz` çıktısı zorunlu

## Tooling stack

| Katman | Araç | Niçin |
|---|---|---|
| Host OS | Mac veya Linux | Apple Silicon'da UTM (free, ARM native) |
| VM runtime | QEMU/KVM (Linux), UTM (Mac) | Free, scriptlenebilir, snapshot iyi |
| VM yönetim | `virsh` CLI + libvirt | Terminal'den kontrol |
| Code sync | VS Code Remote-SSH | Local hissi |
| ISO build (erken) | Cubic GUI | Hızlı iterasyon |
| ISO build (sonra) | live-build + Packer | CI'da otomatik |
| Smoke test | pytest + paramiko (SSH) | "ajanox --version çalışıyor mu" |
| Donanım | Ventoy USB + 1 lab PC | Bare-metal test |

## x86 vs ARM tuzağı

Apple Silicon Mac'te x86_64 ISO emülasyonu çok yavaş (10x). İki seçenek:

1. **ARM64 Ubuntu base'i paralel destekle** — UTM'de native, Pi 5 / ARM laptop bonus
2. **Linux mini-PC al** — x86 dev makinesi, Mac'ten SSH

Birinciyi öneririz — ARM zaten gelecek, şimdi desteklemek bedava farklılaşma.

## Önerilen ilk 3 ay

```
Hafta 1: VM kur, snapshot al, ajanox dev mode bağla
Hafta 2: VS Code Remote-SSH akıcı yap
Hafta 3: Cubic ile ilk ISO çıkar (branding boş, çalışsın)
Hafta 4: Firstrun wizard prototip
Ay 2:    CI'da live-build pipeline
Ay 3:    Ventoy + 1 lab makine + alpha tester programı
```

İlk 2 ay sadece VM yeter. Donanım test fazına v2.0 beta'sından önce gerek yok.
