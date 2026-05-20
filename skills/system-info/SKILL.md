---
name: system-info
version: 0.1.0
description: Sistemin temel durumunu özetler — CPU, RAM, disk, uptime.
ajanox: ">=0.2.0 <1.0.0"
permissions: [shell_safe, system_info]
author:
  name: Özal Yıldırım
  github: yildirimozal
license: Apache-2.0
language: tr
languages: [tr, en]
requires:
  binaries: [uname, uptime, df]
  os: [linux, darwin]
  internet: false
tags: [system, info, monitoring]
---

# System Info Skill

Sistemin temel durumunu özetler. "Bilgisayarım nasıl?", "Disk doldu mu?",
"Ne kadar süredir açık?" gibi sorulara yanıt verir.

## Parametreler

Yok. Skill çağrılır çağrılmaz çalışır.

## Çalıştırılacak komutlar

`bash` tool'u ile sırayla şu komutları çalıştır. Hepsi shell_safe — sessizce
çalışır, runtime onayı gerekmez:

```bash
uname -a
uptime
df -h /
```

## Sonuç işleme

Çıktıları birleştirip kullanıcıya **doğal Türkçe rapor** olarak sun:

- **Sistem:** uname çıktısından OS + sürüm
- **Uptime:** uptime çıktısından "X gün Y saattir açık"
- **Disk:** df çıktısından root partition'ın %doluluk + boş alan

Örnek çıktı:
> Bilgisayarın durumu: macOS 14.5 (Darwin 23.5.0).
> 3 gün 4 saattir açık.
> Disk %78 dolu, 220 GB boş alan kaldı.

## Hata durumları

Bu komutlar tüm Linux/macOS sistemlerde olmalı; hata pek olası değil. Olursa
çıktıyı olduğu gibi göster.
