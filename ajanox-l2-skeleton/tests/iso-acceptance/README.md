# ISO acceptance testleri

QEMU'da otomatik smoke test. ISO build CI'sının son adımı.

## Durum

Boş — Modül A sonunda doldurulacak (ilk ISO çıkınca).

## Senaryolar

```
tests/iso-acceptance/
├── conftest.py                 # QEMU + SSH fixture
├── test_boot.py                # ISO boot edebiliyor mu, GRUB görünüyor mu
├── test_install.py             # autoinstall + cloud-init başarılı mı
├── test_firstrun.py            # wizard başladı mı, tamamlanabilir mi
├── test_ajanox_basic.py        # ajanox --version, ollama list, ilk komut
├── test_gnome_extension.py     # extension yüklü mü, ikon görünüyor mu
└── test_skills.py              # default skill'ler aktif mi
```

## Tech stack

- **pytest** + paramiko (SSH)
- **QEMU/KVM** (headless)
- **expect/pexpect** (boot prompt etkileşim için)

```python
# conftest.py iskeleti
import pytest
import subprocess

@pytest.fixture(scope="session")
def qemu_vm(iso_path, tmp_path_factory):
    disk = tmp_path_factory.mktemp("vm") / "disk.qcow2"
    subprocess.run(["qemu-img", "create", "-f", "qcow2", str(disk), "20G"])
    proc = subprocess.Popen([
        "qemu-system-x86_64",
        "-cdrom", str(iso_path),
        "-drive", f"file={disk},format=qcow2",
        "-m", "8192", "-smp", "4", "-enable-kvm",
        "-nographic",
        "-netdev", "user,id=net0,hostfwd=tcp::2222-:22",
        "-device", "virtio-net,netdev=net0",
    ])
    yield {"ssh_port": 2222}
    proc.terminate()
```

## CI tetikleyici

`.github/workflows/iso.yml` ISO build sonrası bu testleri koşturur.
Tüm test pass = release-ready artifact.

## Smoke test minimumu (v2.0 release kriteri)

- [ ] ISO boot ediyor, GRUB menüsü açılıyor
- [ ] Live session → masaüstüne ulaşıyor
- [ ] Installer çalışıyor, hata vermiyor
- [ ] İlk açılışta wizard başlıyor
- [ ] `ajanox --version` çıktı veriyor
- [ ] `ollama list` qwen2.5 modeli gösteriyor
- [ ] İlk komut çalışıyor: "Bilgisayarın durumu nasıl?"
- [ ] GNOME tray ikonu görünüyor
- [ ] Cmd+Space hotkey quick launcher açıyor

## Donanım uyumluluk (manuel)

Acceptance test'leri VM-only. Bare-metal test için:

- Ventoy USB'ye son ISO'yu at
- En az 3 farklı laptop'ta boot dene
- `lspci`, `lsusb`, `inxi -Fxz` çıktısı kaydet
- `tests/hardware-reports/` altına commit
