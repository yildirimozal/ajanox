---
name: mac-notification
version: 0.1.0
description: macOS'ta masaüstü bildirimi gösterir. Sadece macOS'ta çalışır.
ajanox: ">=0.1.0 <1.0.0"
permissions: [shell_safe, notification]
author:
  name: Özal Yıldırım
  github: yildirimozal
license: Apache-2.0
language: tr
languages: [tr, en]
requires:
  binaries: [osascript]
  os: [darwin]
  internet: false
tags: [notification, macos]
---

# Mac Notification Skill

macOS'un yerleşik bildirim sistemini (`osascript`) kullanarak masaüstü
bildirimi gönderir.

## Parametreler

- `mesaj` (zorunlu): Bildirim metni
- `baslik` (opsiyonel, default: "Ajanox"): Bildirim başlığı

## Çalıştırılacak komut

`bash` tool'u ile şunu çalıştır:

```bash
osascript -e 'display notification "MESAJ" with title "BASLIK"'
```

`MESAJ` ve `BASLIK` yerlerine kullanıcı değerlerini koy. Apostrof varsa
kaçır (`'\''`).

## Sonuç işleme

`osascript` başarılı olunca çıktı dönmez (boş string).

Kullanıcıya kısa onay:
> Bildirim gönderildi: "<mesaj>"

## Hata durumları

- Linux/Windows kullanıcısı: "Bu skill yalnızca macOS'ta çalışır."
- `command not found`: "osascript bulunamadı — bu skill macOS gerektirir."
