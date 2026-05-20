---
name: weather
version: 0.1.0
description: Bir şehrin güncel hava durumunu söyler.
ajanox: ">=0.1.0 <1.0.0"
permissions: [shell_safe, network_read]
author:
  name: Özal Yıldırım
  github: yildirimozal
license: Apache-2.0
language: tr
languages: [tr, en]
requires:
  binaries: [curl]
  internet: true
tags: [weather, info]
---

# Weather Skill

Bir şehrin anlık hava durumunu **wttr.in** servisinden alır. API anahtarı veya
hesap gerektirmez.

## Parametreler

- `sehir` (zorunlu): Şehir adı. Türkçe karakterler İngilizce'ye çevrilmeli
  (İstanbul → Istanbul, Şanlıurfa → Sanliurfa, vb.)

## Çalıştırılacak komut

`bash` tool'u ile şunu çalıştır:

```bash
curl -s 'https://wttr.in/<sehir>?format=3'
```

## Sonuç işleme

Çıktı tek satır gelir, örn: `Istanbul: 🌦 +16°C`.

- Sıcaklığı ve hava koşulunu (güneşli/yağmurlu/karlı/bulutlu) öne çıkar.
- Doğal Türkçe ile akıcı bir cümleyle aktar.

## Hata durumları

- Boş çıktı: "Hava durumu alınamadı, internet bağlantınızı kontrol edin."
- 404 / `Unknown location`: "Şehir bulunamadı: <sehir>"
