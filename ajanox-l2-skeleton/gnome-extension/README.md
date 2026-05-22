# GNOME Shell Extension

Top bar Ajanox tray ikonu + global Cmd+Space hotkey. Modül C.

## Durum

Boş — Modül C (Ay 4) başlangıcında doldurulacak.

## Özellikler

- 🤖 Top bar ikonu, tıkla → dropdown:
  - Quick prompt input (Enter ile gönder)
  - Son 5 konuşma (audit log'tan)
  - "Marketplace aç" → web UI
  - "Web Dashboard aç" → http://localhost:8765
  - "Logs" → audit.log viewer
- **Global hotkey** `Cmd+Space` — herhangi bir ekrandan quick launcher

## İçerik (planlanan)

```
gnome-extension/
├── package.json
├── tsconfig.json
├── src/
│   ├── extension.ts        # entry point
│   ├── indicator.ts        # top bar button + popup
│   ├── quickLauncher.ts    # Cmd+Space overlay
│   ├── ajanoxClient.ts     # ajanox web API'sine HTTP/WS
│   └── settings.ts         # gsettings schema
├── schemas/
│   └── org.ajanox.shell-extension.gschema.xml
├── metadata.json
├── ui/
│   └── prefs.ui            # ayar paneli
└── README.md
```

## Tech stack

- **GNOME Shell 46** (Ubuntu 24.04 default)
- **TypeScript** (type safety, JS'ye derlenir)
- **ESM** (GJS modern modülleri)

```typescript
// extension.ts iskeleti
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export default class AjanoxExtension extends Extension {
    enable() {
        this._indicator = new AjanoxIndicator(this);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }
    disable() {
        this._indicator?.destroy();
    }
}
```

## Ajanox web API ile konuşur

`ajanox web` lokalde 8765'te dinler. Extension HTTP + WebSocket ile bağlanır:

```typescript
// ajanoxClient.ts
const resp = await fetch('http://localhost:8765/api/prompt', {
    method: 'POST',
    body: JSON.stringify({ text: userInput })
});
```

Eğer `ajanox web` çalışmıyorsa extension `systemctl --user start ajanox-web`
ile başlatır (ISO'da user service hazır).

## Dev loop

```bash
# Build
npm install
npm run build  # tsc → dist/

# Zip ve VM'e at
npm run pack
scp dist/ajanox@yildirimozal.com.zip ajanox-dev:~

# VM'de
gnome-extensions install --force ajanox@yildirimozal.com.zip
gnome-extensions enable ajanox@yildirimozal.com.zip
# X11'de: Alt+F2 → "r" → reload
```

Wayland'de reload yok → nested gnome-shell:

```bash
dbus-run-session -- gnome-shell --nested --wayland
```

## Test

- **Unit:** TypeScript pure logic için Vitest
- **E2E:** GNOME Shell'de manuel — automated testing GNOME ekosisteminde zayıf

## Yayınlama

extensions.gnome.org'da yayınlanır. Onay süreci 1-2 hafta. Self-host:
GitHub Releases'tan zip indirilebilir.
