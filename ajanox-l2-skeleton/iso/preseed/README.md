# Preseed (otomatik installer)

Ubuntu Server installer'ı otomatik cevaplandıran dosyalar. Test ISO'larında
kullanıcı etkileşimi olmadan kurulum için gerekli.

## Durum

Boş — Modül A sonunda doldurulacak.

## İçerik (planlanan)

```
preseed/
├── ajanox-default.cfg      # default kurulum (Türkçe, GMT+3, ajanox user)
├── ajanox-test.cfg         # CI smoke test için minimal
└── README.md
```

## Format

Ubuntu 24.04 → `cloud-init` / `autoinstall` (eski preseed.cfg deprecated).

```yaml
# ajanox-default.cfg örneği
#cloud-config
autoinstall:
  version: 1
  locale: tr_TR.UTF-8
  keyboard:
    layout: tr
  timezone: Europe/Istanbul
  identity:
    hostname: ajanox
    username: ajanox
    password: <crypted>
  packages:
    - ajanox-python
    - ollama
  late-commands:
    - curtin in-target -- ajanox-firstrun --setup
```

## Test

```bash
# QEMU'da auto-install
qemu-system-x86_64 -cdrom ajanox.iso \
  -drive file=test.qcow2,format=qcow2 \
  -m 8192 -smp 4 \
  -kernel-irqchip=on \
  -append "autoinstall ds=nocloud-net;s=http://_gateway:3003/"
# Cevaplar HTTP üzerinden servis edilir (cloud-init pattern)
```
