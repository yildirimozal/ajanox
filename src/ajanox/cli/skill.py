"""`ajanox skill` subcommand'leri.

Komutlar:
  init <name> [--user] [--description "..."]   Yeni skill boilerplate üret
  list                                          Yüklü skill'leri listele (sistem + kullanıcı)
  check <path>                                  Bir SKILL.md'nin spec'e uyumunu kontrol et
  install <spec> [--yes]                        Bir skill'i registry/URL'den yükle
  remove <name>                                 Yüklü kullanıcı skill'ini kaldır
  search [query]                                Registry'lerdeki skill'leri listele
  migrate <path>                                v0.x → v1.0 manifest yükseltici (henüz yok)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable

from ..core import registry as reg_mod
from ..core.permissions import (
    FORBIDDEN_PERMISSIONS,
    PERMISSION_RISK,
    RiskLevel,
    validate_permissions,
)
from ..core.skill_loader import Skill, load_skill_catalog, parse_frontmatter


def run(args: list[str]) -> int:
    parser = _build_parser()
    if not args:
        parser.print_help()
        return 1
    ns = parser.parse_args(args)
    return ns.func(ns)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ajanox skill", description="Skill yönetimi")
    sub = parser.add_subparsers(dest="cmd", required=False)

    p_init = sub.add_parser("init", help="Yeni skill boilerplate üret")
    p_init.add_argument("name", help="kebab-case skill adı")
    p_init.add_argument(
        "--user",
        action="store_true",
        help="~/.ajanox/skills/ altına kur (default: cwd/skills/)",
    )
    p_init.add_argument(
        "--description",
        default="",
        help="Kısa açıklama (interactive sorulmazsa)",
    )
    p_init.set_defaults(func=_cmd_init)

    p_list = sub.add_parser("list", help="Yüklü skill'leri tablo halinde göster")
    p_list.add_argument(
        "--source",
        choices=("all", "builtin", "system", "user"),
        default="all",
        help="Hangi kaynaktan listelensin",
    )
    p_list.set_defaults(func=_cmd_list)

    p_check = sub.add_parser("check", help="SKILL.md'nin spec'e uyumunu kontrol et")
    p_check.add_argument("path", help="SKILL.md yolu veya skill klasörü")
    p_check.set_defaults(func=_cmd_check)

    p_install = sub.add_parser("install", help="Bir skill'i registry/URL'den yükle")
    p_install.add_argument(
        "spec",
        help="Skill spec: bare-name | user/repo:name | tam GitHub URL",
    )
    p_install.add_argument(
        "--yes", "-y", action="store_true", help="Onaysız yükle (script'ler için)"
    )
    p_install.set_defaults(func=_cmd_install)

    p_remove = sub.add_parser("remove", help="Yüklü kullanıcı skill'ini kaldır")
    p_remove.add_argument("name", help="Skill adı")
    p_remove.set_defaults(func=_cmd_remove)

    p_search = sub.add_parser("search", help="Registry'lerdeki skill'leri listele")
    p_search.add_argument(
        "query",
        nargs="?",
        default="",
        help="Filtre (skill adında geçen)",
    )
    p_search.set_defaults(func=_cmd_search)

    p_mig = sub.add_parser("migrate", help="v0.x manifest'i v1.0 formatına yükselt")
    p_mig.add_argument("path", nargs="?", default="")
    p_mig.set_defaults(func=_cmd_migrate)

    p_keygen = sub.add_parser("keygen", help="ed25519 imza anahtar çifti üret")
    p_keygen.add_argument(
        "--out", default="", help="Özel anahtarı yazılacak dosya (default: stdout)"
    )
    p_keygen.set_defaults(func=_cmd_keygen)

    p_sign = sub.add_parser("sign", help="Skill'i özel anahtarla imzala (SKILL.md.sig)")
    p_sign.add_argument("path", help="Skill klasörü veya SKILL.md yolu")
    p_sign.add_argument(
        "--key", required=True, help="Özel anahtar dosyası (keygen ile üretilen)"
    )
    p_sign.set_defaults(func=_cmd_sign)

    p_verify = sub.add_parser("verify", help="Skill imzasını doğrula (+ TOFU)")
    p_verify.add_argument("path", help="Skill klasörü veya SKILL.md yolu")
    p_verify.set_defaults(func=_cmd_verify)

    return parser


# ============================================================
# init
# ============================================================
_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")


def _cmd_init(ns: argparse.Namespace) -> int:
    name = ns.name
    if not _NAME_PATTERN.match(name):
        print(
            f"✗ Geçersiz skill adı: '{name}'. kebab-case olmalı (örn. 'my-skill').",
            file=sys.stderr,
        )
        return 1

    target_root = _user_skills_dir() if ns.user else _project_skills_dir()
    skill_dir = target_root / name
    if skill_dir.exists():
        print(f"✗ Skill zaten var: {skill_dir}", file=sys.stderr)
        return 1

    description = ns.description.strip()
    if not description:
        try:
            description = input(f"Description ({name}): ").strip()
        except (EOFError, KeyboardInterrupt):
            description = ""
    if not description:
        description = f"TODO: {name} skill açıklaması"

    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        _boilerplate(name, description), encoding="utf-8"
    )

    print(f"✓ Skill oluşturuldu: {skill_dir}/SKILL.md")
    print(f"  Düzenlemek için: $EDITOR {skill_dir}/SKILL.md")
    print(f"  Kontrol etmek için: ajanox skill check {skill_dir}")
    return 0


def _user_skills_dir() -> Path:
    return Path(os.environ.get("AJANOX_HOME", str(Path.home() / ".ajanox"))) / "skills"


def _project_skills_dir() -> Path:
    return Path.cwd() / "skills"


def _builtin_skills_dir() -> Path:
    """Paket içi yerleşik skill'ler.

    Wheel install: site-packages/ajanox/builtin_skills/
    Dev install: repo root'un skills/ klasörü (fallback).
    """
    pkg_dir = Path(__file__).resolve().parent.parent
    wheel_path = pkg_dir / "builtin_skills"
    if wheel_path.exists():
        return wheel_path
    dev_path = pkg_dir.parent.parent / "skills"
    return dev_path


def _boilerplate(name: str, description: str) -> str:
    title = name.replace("-", " ").title()
    return f"""---
name: {name}
version: 0.1.0
description: {description}
ajanox: ">=1.0.0 <2.0.0"
permissions: [shell_safe]
author:
  name: TODO
  github: TODO
license: Apache-2.0
language: tr
languages: [tr]
requires:
  os: [linux, darwin, wsl]
  internet: false
tags: [todo]
---

# {title} Skill

## Açıklama

{description}

## Parametreler

- TODO: kullanıcıdan hangi parametre alınacak?

## Çalıştırılacak komut

`bash` tool'u ile aşağıdaki komutu çalıştır:

```bash
echo "TODO: gerçek komutu yaz"
```

## Sonuç işleme

Çıktıyı kullanıcıya doğal Türkçe ile aktar.

## Hata durumları

- TODO: hangi hatalar olabilir, nasıl raporlanmalı?
"""


# ============================================================
# list
# ============================================================
def _cmd_list(ns: argparse.Namespace) -> int:
    sources: list[tuple[str, Path]] = []
    if ns.source in ("all", "builtin"):
        builtin = _builtin_skills_dir()
        if builtin.exists():
            sources.append(("builtin", builtin))
    if ns.source in ("all", "system"):
        sys_dir = _project_skills_dir()
        if sys_dir.exists():
            sources.append(("system", sys_dir))
    if ns.source in ("all", "user"):
        user_dir = _user_skills_dir()
        if user_dir.exists():
            sources.append(("user", user_dir))

    all_skills: list[tuple[str, Skill]] = []
    for source, path in sources:
        for skill in load_skill_catalog(path):
            all_skills.append((source, skill))

    if not all_skills:
        print("Yüklü skill yok.")
        print(f"  Sistem: {_project_skills_dir()}")
        print(f"  Kullanıcı: {_user_skills_dir()}")
        print("  Yeni skill için: ajanox skill init <name>")
        return 0

    name_w = max(len(s.name) for _, s in all_skills + [("", _dummy_min())])
    name_w = max(name_w, 20)
    print(f"{'NAME':<{name_w}}  {'VERSION':<10} {'SOURCE':<8} {'PERMISSIONS'}")
    print("-" * (name_w + 50))
    for source, skill in all_skills:
        perms = ", ".join(skill.permissions) if skill.permissions else "(yok)"
        print(f"{skill.name:<{name_w}}  {skill.version:<10} {source:<8} {perms}")
    print(f"\nToplam: {len(all_skills)} skill")
    return 0


def _dummy_min() -> Skill:
    return Skill(name="--------------------", description="", location="")


# ============================================================
# check
# ============================================================
_REQUIRED_FIELDS = ("name", "version", "description", "ajanox", "permissions")
_RECOMMENDED_FIELDS = ("author", "license", "language", "tags")
_RECOMMENDED_BODY_HEADERS = ("Çalıştırılacak komut", "Sonuç işleme", "Hata durumları")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[a-z0-9.]+)?$", re.IGNORECASE)


def _cmd_check(ns: argparse.Namespace) -> int:
    path = Path(ns.path).expanduser()
    if path.is_dir():
        path = path / "SKILL.md"
    if not path.exists():
        print(f"✗ Dosya bulunamadı: {path}", file=sys.stderr)
        return 1

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"✗ Okunamadı: {exc}", file=sys.stderr)
        return 1

    fm = parse_frontmatter(text)
    if not fm:
        print(f"✗ Frontmatter eksik veya parse edilemiyor: {path}", file=sys.stderr)
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    body = text.split("\n---", 2)[-1] if "\n---" in text else ""

    # Zorunlu alanlar
    for field in _REQUIRED_FIELDS:
        if field not in fm:
            errors.append(f"Eksik zorunlu alan: '{field}'")

    # name: kebab-case
    if "name" in fm and not _NAME_PATTERN.match(str(fm["name"])):
        errors.append(f"'name' kebab-case olmalı: '{fm['name']}'")

    # version: semver
    if "version" in fm and not _SEMVER_PATTERN.match(str(fm["version"])):
        errors.append(f"'version' semver olmalı: '{fm['version']}'")

    # permissions: list, geçerli, yasak değil
    if "permissions" in fm:
        perms = fm["permissions"]
        if not isinstance(perms, list):
            errors.append("'permissions' bir liste olmalı (örn. [shell_safe, file_read])")
        else:
            valid, unknown, forbidden = validate_permissions(perms)
            for u in unknown:
                warnings.append(f"Bilinmeyen permission: '{u}'")
            for f in forbidden:
                errors.append(f"YASAK permission: '{f}' (v0.x'te kullanılamaz)")

    # Önerilen alanlar
    for field in _RECOMMENDED_FIELDS:
        if field not in fm:
            warnings.append(f"Önerilen alan eksik: '{field}'")

    # Önerilen body bölümleri
    for header in _RECOMMENDED_BODY_HEADERS:
        if header not in body:
            warnings.append(f"Önerilen body bölümü eksik: '{header}'")

    # Sonuç raporu
    print(f"Skill: {path}")
    print(f"  name:        {fm.get('name', '(yok)')}")
    print(f"  version:     {fm.get('version', '(yok)')}")
    print(f"  permissions: {fm.get('permissions', '(yok)')}")
    print()

    if not errors and not warnings:
        print("✓ Spec ile %100 uyumlu. Hata + uyarı yok.")
        return 0

    if errors:
        print(f"✗ {len(errors)} HATA:")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"⚠ {len(warnings)} uyarı:")
        for w in warnings:
            print(f"  - {w}")

    return 1 if errors else 0


# ============================================================
# install
# ============================================================
def _cmd_install(ns: argparse.Namespace) -> int:
    try:
        registries = reg_mod.load_registries()
        spec = reg_mod.resolve_spec(ns.spec, registries)
    except ValueError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    print(f"İndiriliyor: {spec.raw_url}")
    try:
        content = reg_mod.fetch_skill_md(spec.raw_url)
    except ValueError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    fm = parse_frontmatter(content)
    if not fm:
        print("✗ SKILL.md frontmatter parse edilemiyor.", file=sys.stderr)
        return 1

    skill_name = str(fm.get("name") or spec.name).strip()
    version = str(fm.get("version", "?"))
    description = str(fm.get("description", "(yok)"))
    permissions = fm.get("permissions") or []
    if not isinstance(permissions, list):
        permissions = []

    valid, unknown, forbidden = validate_permissions([str(p) for p in permissions])
    if forbidden:
        print(
            f"✗ YASAK permission içeriyor: {', '.join(forbidden)} — yüklenmedi.\n"
            f"  (Spec C kararı: v0.x'te bu izinler kullanılamaz)",
            file=sys.stderr,
        )
        return 1

    # Manifest preview
    print()
    print("┌─ Skill yükleme onayı " + "─" * 36)
    if spec.registry:
        print(f"│  Kaynak:   {spec.registry.url} (untrusted)")
    print(f"│  Skill:    {skill_name} v{version}")
    print(f"│  Açıklama: {description[:60]}{'…' if len(description) > 60 else ''}")
    if permissions:
        print("│  İzinler:")
        for p in permissions:
            risk = PERMISSION_RISK.get(str(p))
            risk_str = f"({risk.value})" if risk else "(BİLİNMİYOR)"
            marker = (
                "⚠"
                if risk and risk.value in ("high", "critical")
                else "•"
            )
            print(f"│    {marker} {str(p):<18} {risk_str}")
    else:
        print("│  İzinler: (BELIRTILMEMIŞ — legacy mode)")
        print("│    ⚠ Bu skill her tool çağrısı için runtime onay isteyecek.")
        print("│    Yazarına manifest'e permission listesi eklemesini önerin.")
    if unknown:
        print(f"│  ⚠ Bilinmeyen: {', '.join(unknown)}")
    print("└" + "─" * 60)

    if not ns.yes:
        try:
            resp = input("Yükle? [E/h]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if resp not in ("", "e", "evet", "y", "yes"):
            print("İptal edildi.")
            return 0

    path = reg_mod.install_skill_md(skill_name, content)
    print(f"✓ Yüklendi: {path}")
    print(f"  Test: ajanox skill check {path.parent}")
    return 0


# ============================================================
# remove
# ============================================================
def _cmd_remove(ns: argparse.Namespace) -> int:
    if reg_mod.remove_user_skill(ns.name):
        print(f"✓ Kaldırıldı: {ns.name}")
        return 0
    print(f"✗ Yüklü skill bulunamadı: {ns.name}", file=sys.stderr)
    print(f"  (`ajanox skill list --source user` ile yüklü skill'leri gör)", file=sys.stderr)
    return 1


# ============================================================
# search
# ============================================================
def _cmd_search(ns: argparse.Namespace) -> int:
    registries = reg_mod.load_registries()
    if not registries:
        print("Hiç registry kayıtlı değil.", file=sys.stderr)
        return 1

    query = ns.query.lower().strip()
    total = 0
    for r in registries:
        try:
            skills = reg_mod.list_registry_skills(r)
        except ValueError as exc:
            print(f"  ⚠ {r.name}: {exc}", file=sys.stderr)
            continue

        if query:
            skills = [s for s in skills if query in s.lower()]

        if not skills:
            continue

        print(f"\n{r.name} ({r.url}):")
        for s in skills:
            print(f"  • {s}")
            total += 1

    if total == 0:
        print(f"\n(Hiç sonuç yok{f' — filtre: {query}' if query else ''})")
    else:
        print(f"\nToplam: {total} skill")
        print("Yüklemek için: ajanox skill install <name>")
    return 0


# ============================================================
# migrate (stub)
# ============================================================
_AJANOX_LINE = re.compile(r'^(ajanox:\s*").*?(")\s*$', re.MULTILINE)


def _cmd_migrate(ns: argparse.Namespace) -> int:
    """SKILL.md'yi v1.0 formatına yükselt.

    Şu an: `ajanox` constraint üst sınırını `<1.0.0` → `<2.0.0` yapar
    (1.x serisiyle uyumlu hale getirir). Eksikse `>=1.0.0 <2.0.0` ekler.
    """
    if not ns.path:
        print("✗ Kullanım: ajanox skill migrate <skill-dizini>", file=sys.stderr)
        return 1

    skill_md = _resolve_skill_md(ns.path)
    if not skill_md:
        print(f"✗ SKILL.md bulunamadı: {ns.path}", file=sys.stderr)
        return 1

    text = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    old = str(fm.get("ajanox", "")).strip()

    if "<1.0.0" in old:
        new = old.replace("<1.0.0", "<2.0.0")
    elif not old:
        new = ">=1.0.0 <2.0.0"
    else:
        print(f"✓ '{skill_md.parent.name}' zaten güncel (ajanox: \"{old}\") — değişiklik yok")
        return 0

    if _AJANOX_LINE.search(text):
        updated = _AJANOX_LINE.sub(rf'\g<1>{new}\g<2>', text, count=1)
    else:
        # ajanox satırı yok — frontmatter'a ekle (ilk --- sonrası)
        updated = text.replace("---\n", f'---\najanox: "{new}"\n', 1)

    skill_md.write_text(updated, encoding="utf-8")
    print(f"✓ '{skill_md.parent.name}' yükseltildi: ajanox: \"{old or '(yok)'}\" → \"{new}\"")
    return 0


# ============================================================
# keygen / sign / verify (skill imzalama — v0.9)
# ============================================================
def _resolve_skill_md(raw: str) -> Path | None:
    """Klasör veya dosya yolundan SKILL.md'yi bul."""
    path = Path(raw).expanduser()
    if path.is_dir():
        path = path / "SKILL.md"
    return path if path.exists() else None


def _skill_name_from_md(skill_md: Path) -> str:
    """SKILL.md frontmatter'ından name; yoksa klasör adı."""
    try:
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        name = str(fm.get("name", "")).strip()
        if name:
            return name
    except OSError:
        pass
    return skill_md.parent.name


def _cmd_keygen(ns: argparse.Namespace) -> int:
    from ..core import signing

    try:
        priv, pub = signing.generate_keypair()
    except signing.SigningUnavailable as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    if ns.out:
        out = Path(ns.out).expanduser()
        out.write_text(priv + "\n", encoding="utf-8")
        try:
            out.chmod(0o600)
        except OSError:
            pass
        print(f"✓ Özel anahtar yazıldı: {out} (chmod 600)")
        print(f"  Public key: {pub}")
        print("  ⚠ Özel anahtarı GİZLİ tut, paylaşma. Public key'i skill ile dağıt.")
    else:
        print("# Özel anahtar (GİZLİ — dosyaya kaydet, paylaşma):")
        print(priv)
        print("# Public key (skill ile dağıtılabilir):")
        print(pub)
    return 0


def _cmd_sign(ns: argparse.Namespace) -> int:
    from ..core import signing

    skill_md = _resolve_skill_md(ns.path)
    if not skill_md:
        print(f"✗ SKILL.md bulunamadı: {ns.path}", file=sys.stderr)
        return 1

    key_path = Path(ns.key).expanduser()
    if not key_path.exists():
        print(f"✗ Anahtar dosyası yok: {key_path}", file=sys.stderr)
        return 1

    private_hex = key_path.read_text(encoding="utf-8").strip()
    try:
        sig_path = signing.sign_file(skill_md, private_hex)
    except signing.SigningUnavailable as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"✗ Geçersiz anahtar: {exc}", file=sys.stderr)
        return 1

    print(f"✓ İmzalandı: {sig_path}")
    print(f"  Skill: {_skill_name_from_md(skill_md)}")
    print(f"  Public key: {signing.public_from_private(private_hex)}")
    return 0


def _cmd_verify(ns: argparse.Namespace) -> int:
    from ..core import signing

    skill_md = _resolve_skill_md(ns.path)
    if not skill_md:
        print(f"✗ SKILL.md bulunamadı: {ns.path}", file=sys.stderr)
        return 1

    skill_name = _skill_name_from_md(skill_md)
    try:
        result = signing.verify_file(skill_md, skill_name)
    except signing.SigningUnavailable as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    if not result.valid:
        print(f"✗ İmza GEÇERSİZ — {result.error}", file=sys.stderr)
        return 1

    if result.trust == "changed":
        print(f"⚠ İmza geçerli AMA yazar anahtarı DEĞİŞTİ — '{skill_name}'", file=sys.stderr)
        print(f"  Önceki anahtar: {result.previous_pubkey}", file=sys.stderr)
        print(f"  Şimdiki anahtar: {result.pubkey}", file=sys.stderr)
        print(
            "  Bu beklenen bir güncellemeyse: ~/.ajanox/trust/ altındaki dosyayı\n"
            "  sil ve tekrar verify et. Beklenmiyorsa KURMA — kimlik sahteciliği olabilir.",
            file=sys.stderr,
        )
        return 2

    label = "yeni yazar — anahtar TOFU deposuna kaydedildi" if result.trust == "new" else "bilinen yazar"
    print(f"✓ İmza geçerli ({label})")
    print(f"  Skill: {skill_name}")
    print(f"  Public key: {result.pubkey}")
    return 0
