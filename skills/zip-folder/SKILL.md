---
name: zip-folder
version: 0.1.0
description: Bir klasörü tarihe göre zip'leyerek ~/Downloads klasörüne yedekler.
icon: "📦"
example_prompt: "belgelerim klasörünü yedekle"
ajanox: ">=0.2.0 <2.0.0"
permissions: [shell_safe, shell_unsafe, file_write]
author:
  name: Süleyman Sardoğan
  github: suleymanssardogan
license: Apache-2.0
language: tr
languages: [tr, en]
requires:
  binaries: [zip]
  os: [linux, darwin]
  internet: false
tags: [filesystem, backup, zip]
---

# Klasör Yedek Skill

Belirtilen klasörü alır, tarihe göre zip dosyası oluşturur.
Zip dosyası her zaman $HOME/Downloads klasörüne kaydedilir.

## Parametreler

- `klasor` (zorunlu): yedeklenecek klasörün yolu. Türkçe ifadeleri çevir:
  - "belgelerim" / "dökümanlar" → `$HOME/Documents`
  - "masaüstü" → `$HOME/Desktop`
  - "indirilenler" → `$HOME/Downloads`
  - "test-klasor" → `$HOME/test-klasor`
  - Tam yol verilirse (`/tmp/foo`, `/home/user/proje`) olduğu gibi kullan.

## Çalıştırılacak komut (TEK SATIRDA)

Zip dosyası HER ZAMAN $HOME/Downloads klasörüne kaydedilir.
`~` yerine `$HOME` kullan (sandbox uyumluluğu için):

```bash
zip -r "$HOME/Downloads/<klasor_adi>_$(date +%Y-%m-%d).zip" "<tam_klasor_yolu>"
```

Örnekler:
```bash
zip -r "$HOME/Downloads/Documents_$(date +%Y-%m-%d).zip" "$HOME/Documents"
zip -r "$HOME/Downloads/test-klasor_$(date +%Y-%m-%d).zip" "$HOME/test-klasor"
zip -r "$HOME/Downloads/foo_$(date +%Y-%m-%d).zip" "/tmp/foo"
```

## Sonuç işleme

- Başarılı (exit 0): "Yedek oluşturuldu: $HOME/Downloads/<klasor_adi>_<tarih>.zip"
- Klasör bulunamazsa (exit 12): "Klasör bulunamadı: <yol>"
- Disk doluysa (exit 1): "Yeterli disk alanı yok"
