# First-boot wizard

Kullanıcı ilk açıldığında karşılayan Türkçe GTK sihirbazı. Modül B.

## Durum

Boş — Modül B (Ay 3) başlangıcında doldurulacak.

## Akış

```
1. Hoş geldin (logo + tagline)
2. Dil seçimi (TR/EN, v2.1+'ta diğer diller)
3. Kullanıcı oluştur (ad + parola + hostname)
4. Ağ + saat dilimi
5. "Ajanox nedir? 60 saniyede" → kısa video/GIF
6. Ollama'yı doğrula (model ISO'da, sadece check)
7. Marketplace tanıt (5 önerilen skill)
8. İlk komutu dene: "Bilgisayarın durumu nasıl?" → çalışır mı
9. Tamam → masaüstüne dön + tray ikonu görünür
```

## İçerik (planlanan)

```
firstrun/
├── pyproject.toml          # PyGObject deps
├── ajanox_firstrun/
│   ├── __main__.py
│   ├── wizard.py           # ana state machine
│   ├── pages/
│   │   ├── welcome.py
│   │   ├── language.py
│   │   ├── account.py
│   │   ├── network.py
│   │   ├── intro_video.py
│   │   ├── ollama_check.py
│   │   ├── marketplace.py
│   │   └── first_command.py
│   ├── assets/
│   │   ├── logo.svg
│   │   └── intro.gif
│   └── i18n/
│       ├── tr.po
│       └── en.po
└── tests/
```

## Tech stack

- **GTK 4** (Ubuntu 24.04 default)
- **PyGObject** (Python binding)
- **Adwaita** (GNOME design tokens)

```python
# wizard.py iskeleti
from gi.repository import Gtk, Adw

class AjanoxWizard(Adw.ApplicationWindow):
    def __init__(self):
        super().__init__()
        self.set_title("Ajanox'a hoş geldin")
        self.stack = Gtk.Stack()
        # ... her sayfa Adw.NavigationPage
```

## Trigger

İlk login'de `~/.config/ajanox/firstrun-done` dosyası yoksa `gnome-session`
autostart ile tetiklenir:

```ini
# /etc/skel/.config/autostart/ajanox-firstrun.desktop
[Desktop Entry]
Type=Application
Exec=ajanox-firstrun
X-GNOME-Autostart-enabled=true
```

Wizard biter → `firstrun-done` dosyasını yazar, autostart entry'sini siler.

## Test

```bash
# Manuel
python -m ajanox_firstrun --debug

# VM snapshot rollback ile e2e
virsh snapshot-revert ajanox-dev fresh
virsh start ajanox-dev
# wizard otomatik başlar
```
