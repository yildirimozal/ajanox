---
name: delete-old-logs
version: 0.1.0
description: Belirli bir klasörde N günden eski log dosyalarını listeler, onay aldıktan sonra siler.
ajanox: ">=0.2.0 <1.0.0"
permissions: [shell_safe, shell_unsafe, file_write]
author:
  name: Özal Yıldırım
  github: yildirimozal
license: Apache-2.0
language: tr
languages: [tr, en]
requires:
  binaries: [find, rm]
  os: [linux, darwin]
  internet: false
tags: [filesystem, cleanup, logs]
---

# Delete Old Logs Skill

Belirli bir klasörde N günden eski log dosyalarını bulup siler. Bu, klasik
"30 günden eski log dosyalarını sil" senaryosunun referans implementasyonudur.

## Parametreler

- `klasor` (zorunlu): aranacak yol. Türkçe ifadeleri İngilizce'ye çevir:
  - "log klasörü" → `/var/log` (Linux) veya `~/Library/Logs` (macOS)
  - "indirilenler" → `~/Downloads`
- `gun` (opsiyonel, default: 30): kaç günden eski

## Çalıştırılacak komutlar (SIRAYLA, AYNI TURDA, DURMA)

### Adım 1: Listele
```bash
find <klasor> -type f -name "*.log" -mtime +<gun>
```

Bu komut shell_safe — sessizce çalışır.

### Adım 2: Hemen Sil (komut çıktısı boş değilse)

**Kullanıcıya hiçbir şey sormadan**, doğrudan rm çağır:

```bash
rm -f <dosya1> <dosya2> ...
```

`<dosya1> <dosya2>` yerine Adım 1'in çıktısındaki dosya yollarını koy.

**KRİTİK:** "Silmek istiyor musunuz?" diye SORMA. Doğrudan rm bash çağrısını
yap. Çünkü:
- `rm` shell_unsafe kategorisindedir
- Ajanox güvenlik katmanı zaten runtime'da kullanıcıya görünür onay sorusu
  çıkaracak ([E]vet/[H]ayır/[T]ümü)
- Skill'in görevi komutu hazırlamak; kullanıcıyı onaylatmak ASLA SKILL'İN İŞİ
  DEĞİL — runtime'ın işi
- Eğer sorarsan: kullanıcı iki kere onay vermek zorunda kalır → kötü UX

## Sonuç işleme

- rm başarılı (exit 0): "X dosya silindi" rapor et
- rm reddedildi (Ajanox güvenlik onay vermedi): "İşlem iptal edildi, dosyalar duruyor"
- Liste boştu: "<gun> günden eski log dosyası yok, silinecek bir şey yok"

## Hata durumları

- Klasör yoksa: "Klasör bulunamadı: <yol>"
- Permission denied (sistem koruması): "İzin hatası: <detay>" — sudo isteme
- macOS `/var/log` SIP korumalı; `~/Library/Logs` yazılabilir

## Güvenlik notu

`shell_unsafe` ve `file_write` permission'larını gerektirir. Critical path
(`~/.ssh`, `/etc`, ...) altında bir log dosyasına dokunulursa Ajanox
ekstra onay katmanı devreye girer ve "T (Tümünü onayla)" opsiyonu KAPALI olur.
