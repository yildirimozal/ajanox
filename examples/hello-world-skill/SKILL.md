---
name: hello-world
version: 0.1.0
description: Selam veren örnek skill. Yeni başlayanlar için template.
ajanox: ">=0.1.0 <1.0.0"
permissions: [shell_safe]
author:
  name: Ajanox Team
license: Apache-2.0
language: tr
languages: [tr, en]
requires:
  os: [linux, darwin]
  internet: false
tags: [example, tutorial]
---

# Hello World Skill

Bu, Ajanox'a skill yazmayı öğrenmek için en küçük örnek. Kullanıcıya Türkçe
selam verir.

## Parametreler

- `isim` (opsiyonel, default: `dünya`): Kime selam verilecek

## Çalıştırılacak komut

`bash` tool'u ile:

```bash
echo "Merhaba <isim>! Ajanox'a hoş geldin."
```

## Sonuç işleme

Çıktıyı doğrudan kullanıcıya aktar — değiştirmeye gerek yok.

## Hata durumları

Bu skill hatasız çalışmalı. `echo` her sistemde var.
