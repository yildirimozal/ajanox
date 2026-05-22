# ISO build

İki yol: **Cubic** (v2.0 prototip, hızlı) ve **live-build** (v2.1+, CI otomatik).

## Cubic ile (v2.0)

GUI tabanlı, click-based. Öğrenme eğrisi düşük, ilk ISO çıkarmak için doğru
araç.

### Kurulum

```bash
sudo add-apt-repository ppa:cubic-wizard/release
sudo apt update
sudo apt install cubic
```

### İlk ISO

1. `cubic` çalıştır
2. Working directory seç: `iso/cubic/build-v2.0/`
3. Ubuntu 24.04.x Desktop ISO seç (cubic indirir veya manuel verebilirsin)
4. Customize → terminal açılır (chroot'a girdin)

```bash
# chroot içinde:
apt update
apt install -y python3-pip
curl -fsSL https://ollama.ai/install.sh | sh
pip install 'ajanox[web]==1.0.0'

# Model'i ISO'ya göm (~9 GB):
ollama serve &
ollama pull qwen2.5:14b

# Default skill'ler
ajanox skill install system-info
ajanox skill install network-info
ajanox skill install disk-cleanup
ajanox skill install process-manager

# Firstrun script
cp /tmp/ajanox-firstrun.py /etc/skel/.config/ajanox/

# Branding
cp /tmp/wallpaper.png /usr/share/backgrounds/ajanox.png

exit
```

5. Cubic → Generate → ~10 dk → `ajanox-2.0-amd64.iso` (~12 GB)

### Test

```bash
# QEMU'da boot et
qemu-system-x86_64 -cdrom ajanox-2.0-amd64.iso \
  -m 8192 -smp 4 -enable-kvm \
  -display gtk
```

## live-build ile (v2.1+)

CI otomasyonu için. Configs `iso/live-build/` altında.

### Kurulum

```bash
sudo apt install live-build
```

### Build

```bash
cd iso/live-build
sudo lb config \
  --distribution noble \
  --architecture amd64 \
  --linux-flavours generic \
  --debian-installer live \
  --archive-areas "main restricted universe multiverse"

# Custom paketler ve hooks zaten config/'de hazır
sudo lb build  # ~30-40 dk

ls -lh *.hybrid.iso
```

### CI'da

`.github/workflows/iso.yml` her push'ta tetiklenir. Bkz: workflows/iso.yml.

Artifact GitHub Releases'a yüklenir. >2 GB için release asset yerine
external mirror (Backblaze B2 veya BitTorrent) düşünülmeli.

## ISO içeriği kontrolü

```bash
# ISO'yu mount et
sudo mount -o loop ajanox-2.0-amd64.iso /mnt
ls /mnt/casper/  # squashfs burada
sudo umount /mnt

# squashfs içeriği
sudo unsquashfs -l /mnt/casper/filesystem.squashfs | grep ajanox
```

## Boyut optimizasyonu

Hedef: 12 GB altı. Ana yer kaplayan:

- qwen2.5:14b model → ~9 GB (sıkıştırılamaz)
- Ubuntu desktop base → ~3 GB
- GNOME + apps → ~1 GB
- Ajanox + skills → ~50 MB

**Boyut azaltma seçenekleri:**

- Default model `qwen2.5:7b` (~5 GB), 14b opsiyonel post-install indirme
- Snap paketleri kaldır (~500 MB)
- LibreOffice çıkar (~400 MB) — geliştirici hedefli, gerekmez

## Sorun giderme

| Hata | Çözüm |
|---|---|
| Cubic chroot'ta `apt` askıda kalıyor | `/etc/resolv.conf` mount'unu kontrol et |
| Ollama ISO içinde model bulamıyor | `OLLAMA_MODELS=/usr/share/ollama/models` export et |
| ISO boot'ta GRUB error | `iso/preseed/grub.cfg` doğru mu, syslinux conflict mi |
| ISO 4 GB üstü = FAT32 sınırı | UEFI USB için uyarı göster, Ventoy öner |
