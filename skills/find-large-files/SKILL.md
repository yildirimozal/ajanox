---
name: find-large-files
version: 0.1.0
description: Bir klasördeki en büyük dosyaları ve alt klasörleri listeler.
ajanox: ">=0.1.0 <1.0.0"
permissions: [shell_safe, file_read]
author:
  name: Özal Yıldırım
  github: yildirimozal
license: Apache-2.0
language: tr
languages: [tr, en]
requires:
  binaries: [du, sort, head]
  os: [linux, darwin]
  internet: false
tags: [filesystem, disk-usage, cleanup]
---

# Find Large Files Skill

Bir klasörde yer kaplayan en büyük öğeleri bulmak için `du` kullanır.

## Parametreler

- `klasor` (zorunlu): Aranacak yol. Kullanıcı Türkçe söylediyse İngilizce
  yola çevir:
  - "İndirilenler" → `~/Downloads`
  - "Masaüstü" → `~/Desktop`
  - "Belgeler" → `~/Documents`

## Çalıştırılacak komut

`bash` tool'u ile şunu çalıştır:

```bash
du -ah <klasor> 2>/dev/null | sort -hr | head -10
```

## Sonuç işleme

- En büyük 3-5 öğeyi öne çıkar.
- Boyutları okunabilir formatla (du -h zaten okunabilir).
- Silme komutu **ASLA çalıştırma** — sadece raporla.

## Hata durumları

- Klasör yoksa: "Klasör bulunamadı: <yol>"
- Boş çıktı: "Klasör boş veya erişim izni yok."
