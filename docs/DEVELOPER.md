# Geliştirici Rehberi — Skill Yazma

> Bu rehber, Ajanox için yeni bir skill yazmayı 10 dakikada anlatır.

## Skill nedir?

Tek bir Markdown dosyası — `SKILL.md`. İçinde:
- **Frontmatter** (manifest): isim, sürüm, izinler, vs.
- **Body**: LLM'in göreceği talimat metni

Bu kadar. Python yok, kayıt yok, derleme yok.

## 1. Boilerplate üret

```bash
ajanox skill init merhaba-dunya
```

Bu, `~/.ajanox/skills/merhaba-dunya/SKILL.md` oluşturur.

## 2. SKILL.md'yi düzenle

Minimal şablon:

```markdown
---
name: merhaba-dunya
version: 0.1.0
description: Türkçe bir merhaba der.
ajanox: ">=0.1.0 <1.0.0"
permissions: [shell_safe]
author:
  name: Adınız Soyadınız
  github: kullanici-adi
license: Apache-2.0
language: tr
---

# Merhaba Dünya Skill

Bu skill, kullanıcıya Türkçe bir selam vermek için kullanılır.

## Parametreler

- `isim` (opsiyonel, default: "dünya"): kime selam verilecek

## Çalıştırılacak komut

`bash` tool'u ile:

```bash
echo "Merhaba <isim>!"
```

## Sonuç işleme

Çıktıyı kullanıcıya aynen aktar.
```

## 3. Permission seç

Skill'in ne yapacağına göre [SPEC.md](SPEC.md) §3 tablosundan permission seç:

- Sadece dosya okuyorsa → `file_read`
- Kısıtlı shell komutu (ls, du, cat) → `shell_safe`
- Keyfi shell komutu → `shell_unsafe` (kullanıcı her seferinde onaylar)
- HTTP GET → `network_read`
- HTTP POST → `network_write` (yüksek risk)

**Kural:** en az permission'ı iste. Az isteyen skill kullanıcıdan daha çabuk onay alır.

## 4. Test et

```bash
ajanox skill check ~/.ajanox/skills/merhaba-dunya/SKILL.md
```

Linter manifest'i doğrular, body önerilerine uyumu rapor eder.

Sonra Ajanox'u başlat:
```bash
ajanox
```
Sen: merhaba ahmet
Skill listesinde göreceksin ve LLM uygun durumlarda kullanacak.

## 5. Yayınla (v0.5+ marketplace ile)

```bash
ajanox skill publish ~/.ajanox/skills/merhaba-dunya/
```

(Henüz marketplace yok — şimdilik GitHub'da paylaş.)

## En iyi pratikler

- **Description net olsun**: LLM bu cümleyi okuyup "bu skill mi?" diye karar verir.
  "Bir şey yapar" değil, "30 günden eski log dosyalarını siler" yazın.
- **Komutu açıkça yazın**: SKILL.md body'sinde `<klasor>` gibi placeholder'ları LLM
  doldurur, ama format net olmazsa hata yapar.
- **Hata durumlarını listele**: "Klasör yoksa şunu söyle, internet yoksa şöyle yap."
- **Silme/yazma yapan skill'lerde dry-run önerin**: kullanıcı önce ne silineceğini
  görsün, sonra onay.
- **Türkçe + İngilizce**: hedef kitle uluslararası ise iki dil de yazın
  (`languages: [tr, en]`).

## Daha fazla

- Spec: [SPEC.md](SPEC.md)
- Mimari: [ARCHITECTURE.md](ARCHITECTURE.md)
- Güvenlik: [SECURITY.md](SECURITY.md)
- Örnekler: [../examples/](../examples/) ve [../skills/](../skills/)
