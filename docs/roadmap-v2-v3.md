# Ajanox v2.0 + v3.0 — Yol Haritası

> v0.5.0'dan (Mayıs 2026) v2.0 (Ubuntu Remix) ve v3.0 (eBPF kernel policy)
> aşamalarına nasıl gideceğimiz. **Sıfırdan kernel YOK** — mevcut Linux
> altyapısının üstüne stratejik genişleme.

---

## Durum: Şu an neredeyiz (v0.5.0, Mayıs 2026)

L3 (Ubuntu/macOS üstüne paket). `pip install ajanox[web]` çalışıyor. 12
release, 97 test, public PyPI + GitHub.

**Sonraki büyük adım iki yıllık vizyon:**
- **v1.0** (6 ay sonra) — L3'ün stabil hali
- **v2.0** (12-18 ay sonra) — L2: Ajanox Linux Remix
- **v3.0** (24+ ay sonra) — eBPF/LSM ile kernel-derinliği

---

## Tablo: Spektrum tekrar

| Seviye | Ne | Süre | Risk | Ajanox planı |
|---|---|---|---|---|
| **L3** | Mevcut OS üstüne paket | (yapıldı) | düşük | **v0.x → v1.x** ✓ |
| **L2** | Ubuntu fork, kendi userspace | 6-12 ay | orta | **v2.0** |
| **L1** | Kernel fork, ayrı kernel | 2-5 yıl | yüksek | **ASLA** |
| **L0** | Sıfırdan kernel | 5-10+ yıl | imkansız (solo) | **ASLA** |

---

## v1.0 — L3 Stabilize (önce bunu bitir)

v2.0'a girmeden önce yapılması gerekenler. **6 ay tahmini.**

| Milestone | Çıktı |
|---|---|
| **v0.6** | Tool-call verification (halüsinasyon koruma) |
| **v0.7** | Sandbox default-on (`sandbox-exec` + `bwrap`) |
| **v0.8** | Cross-platform (Windows WSL2 testleri) |
| **v0.9** | Domain allowlist + skill imzalama + sandbox |
| **v1.0** | API stabilizasyonu — Spec donar, breaking change v2.0'a kadar yok |

**Ekosistem hedefleri:**
- 50+ topluluk skill (marketplace'te)
- 1000+ haftalık PyPI download
- 5+ contributor (kod commit)
- Türkçe ve İngilizce dokümantasyon eşit

**v1.0 kriterleri:**
- ✓ Skill Spec donmuş
- ✓ Tool-call verification (halüsinasyon yok)
- ✓ Sandbox default
- ✓ 3 platform (macOS + Linux + WSL2) test edilmiş
- ✓ Performance: 14B inference ile <5s avg response

---

## v2.0 — Ubuntu Remix (L2)

**Hedef:** Pop_OS modeli. Ubuntu 24.04 LTS base + Ajanox = ayrı bir distro,
kendi ISO, kendi installer, default Ajanox shell.

### 1. Mimari kararı: Cubic vs live-build

| | Cubic | live-build |
|---|---|---|
| **Tip** | GUI tool, click-based | CLI, scriptable |
| **Öğrenme eğrisi** | Düşük | Orta |
| **CI/CD entegrasyon** | Manuel | Otomatik |
| **Karmaşık customization** | Sınırlı | Sınırsız |
| **Resmi destek** | Ubuntu remix community | Debian project |

**Önerim:** v2.0 prototip için **Cubic** (hızlı iterasyon), v2.1+'ta
**live-build** (CI'da otomatik build).

### 2. Yapı taşları (6 ana modül)

#### Modül A — Custom ISO (~2 ay)
Ubuntu 24.04 LTS ISO + Cubic chroot içinde:
```bash
# Cubic GUI'de
apt update && apt install -y python3-pip ollama-cli
pip install 'ajanox[web]==2.0.0'

# Modeli ISO'ya göm (~9 GB)
ollama pull qwen2.5:14b

# Default skill paketi
ajanox skill install system-info
ajanox skill install network-info
ajanox skill install disk-cleanup
ajanox skill install process-manager

# Custom firstrun script
cp ajanox-firstrun.py /etc/skel/.config/ajanox/

# Branding
cp wallpaper.png /usr/share/backgrounds/ajanox.png
update-alternatives --set desktop-base-default ajanox
```

**Çıktı:** `ajanox-2.0-amd64.iso` (~12 GB, model dahil)

#### Modül B — First-boot Wizard (~2 hafta)

Kullanıcı ilk açıldığında karşılayan wizard. **Türkçe + İngilizce.**

```
1. Hoş geldin (logo + tagline)
2. Dil seçimi (TR/EN default'tan başka diller v2.1+)
3. Kullanıcı oluştur (ad + parola + hostname)
4. Ağ + saat dilimi
5. "Ajanox nedir? 60 saniyede" → kısa video/GIF
6. Ollama'yı doğrula (model ISO'da, sadece check)
7. Marketplace'i göster (5 önerilen skill)
8. İlk komutu dene: "Bilgisayarın durumu nasıl?" → çalışır mı
9. Tamam → masaüstüne dön + tray ikonu görünür
```

Implementation: PyGObject (GTK 4) ile Türkçe TUI. Kod `~/.config/ajanox/firstrun.py`.

#### Modül C — GNOME Shell Extension (~4 hafta)

Top bar'da 🤖 Ajanox ikonu, tıkla → küçük dropdown:
- Quick prompt input (Enter ile gönder)
- Son 5 konuşma
- "Marketplace aç" → web UI
- "Web Dashboard aç" → http://localhost:8765
- "Logs" → audit.log viewer

**Global hotkey:** `Cmd+Space` (macOS Spotlight benzeri) — herhangi bir
ekrandan Ajanox quick launcher açılır. GNOME ShortcutManager API.

Implementation: JavaScript (GNOME Shell extension), TypeScript yazılır,
build pipeline'la deploy edilir.

#### Modül D — Brand Identity (~2 hafta)

Tasarımcı ile çalışma gerekli:
- **Logo** — minimal, akılda kalıcı, scalable (favicon-512px)
- **Color palette** — Ajanox blue (#7c9eff) + accent green
- **Wallpaper set** — 5 varyasyon (gündüz/gece/abstract)
- **GRUB tema** — bootloader ekranı
- **GNOME Shell theme** — koyu varyant
- **Login screen** — splash + animasyon
- **Sticker/T-shirt mockup** — topluluk için

**Tahmini bütçe:** 1500-3000 USD freelance designer (Behance/Dribbble).

#### Modül E — APT Repository / PPA (~1 hafta)

Launchpad'de PPA: `ppa:yildirimozal/ajanox`

```bash
# Son kullanıcı:
sudo add-apt-repository ppa:yildirimozal/ajanox
sudo apt update && sudo apt install ajanox
sudo apt upgrade ajanox  # update mekanizması
```

Build pipeline: GitHub Actions → `dput` ile Launchpad'e push → otomatik build.

#### Modül F — Sistem Yönetimi Skill Paketi (~3 hafta)

Mevcut 5 builtin + 10-15 yeni sistem skill'i:

| Skill | Ne yapar | Permission |
|---|---|---|
| `system-update` | `apt update && apt upgrade` | shell_unsafe + sudo (v1.0'da gelir) |
| `network-info` | IP, DNS, route table | shell_safe + network_read |
| `disk-cleanup` | apt cache temizle, eski log'lar | file_write + shell_unsafe |
| `process-manager` | top + kill ile process yönetimi | process_read + process_control |
| `wifi-manage` | Wi-Fi ağlarına bağlan | shell_unsafe + sudo |
| `bluetooth-pair` | BT cihaz eşleştir | shell_unsafe |
| `screenshot` | Ekran görüntüsü al | shell_safe + clipboard |
| `clipboard-history` | Pano geçmişi | clipboard |
| `volume-control` | Ses kontrol | system_info + shell_safe |
| `brightness` | Ekran parlaklık | system_info + shell_safe |
| `battery-status` | Pil durumu + tahmini süre | system_info |
| `vpn-connect` | VPN bağlantısı (WireGuard/OpenVPN) | shell_unsafe + network_write |
| `terminal-spawn` | Yeni terminal pencere aç | shell_safe |
| `app-launch` | Uygulama başlat (.desktop entries) | shell_safe |
| `file-search` | locate/mlocate ile dosya ara | file_read + shell_safe |

Her biri test edilmiş + manifest tam.

### 3. Timeline (solo geliştirici tahmini)

```
Ay 1-2:  Modül A (ISO build pipeline)
Ay 3:    Modül B (First-boot wizard)
Ay 4:    Modül C (GNOME extension)
Ay 5:    Modül D (Brand identity — paralel başlar)
Ay 6:    Modül E + F (APT + sistem skills)

Ay 7:    Alpha test (kapalı, 10-20 tester)
Ay 8:    Beta (public, GitHub releases)
Ay 9:    Bug fix + polish
Ay 10:   v2.0 stable release
```

**Solo: 10 ay. 3 kişilik takım: 4 ay. Profesyonel distro takımı: 6 hafta.**

### 4. Karar noktaları

| Karar | Seçenekler | Önerim |
|---|---|---|
| **Base distro** | Ubuntu, Debian, Fedora | Ubuntu 24.04 LTS (en geniş driver, en iyi Ollama desteği) |
| **Desktop env** | GNOME, KDE, Cinnamon | GNOME (Ubuntu default, en iyi Türkçe desteği) |
| **Init system** | systemd | systemd (kaçınılmaz, atomic alternatif gereksiz karmaşık) |
| **Paket yöneticisi** | apt | apt (Ubuntu base, PPA olgun) |
| **Default browser** | Firefox, Chromium | Firefox (Türkçe + privacy) |
| **Default editor** | VS Code, Vim, GNOME Text | VS Code (geliştirici hedefli) |
| **Default terminal** | GNOME Terminal, Wezterm | Wezterm (modern, Ajanox tema'sı uygulanabilir) |

### 5. Dağıtım stratejisi

**ISO dağıtım:**
- GitHub Releases (ana kaynak, ~12 GB → LFS veya external)
- **Türkiye mirror'ları:** ULAKBIM, üniversite ağları (TÜBİTAK ile görüş)
- BitTorrent magnet link (decentralized)
- DistroWatch entry (resmi listede)

**Marketing:**
- Linux haber siteleri: OMG Ubuntu, It's FOSS, Phoronix
- Türkiye: Hürriyet Tech, Webrazzi
- Reddit: r/linux, r/Ubuntu, r/MachineLearning
- Hacker News (launch günü)
- YouTube: Distro review kanalları (Chris Titus, DistroTube)

---

## v3.0 — eBPF + LSM (kernel-derinliği policy)

**Hedef:** Linux kernel'in mevcut eBPF altyapısını kullanarak Ajanox'un
permission sistemini **kernel-seviyesi**'ne çıkar. Hâlâ kernel YAZMAYIZ —
sadece içine sandboxed kod inject ederiz.

### Niçin gerekli? (motivasyon)

L3 + L2'de sınırlama: Ajanox'un permission sistemi sadece **Ajanox-içi**
çalışıyor. Kullanıcı başka terminal'den `rm -rf ~/` yapsa Ajanox bilmez,
yakalayamaz. Kötü amaçlı bir skill bash dışı bir yol bulabilir.

eBPF ile **sistem geneli enforcement**:
- Tüm syscall'lar Ajanox audit log'da görünür
- Skill'in declare etmediği komut, kernel seviyesinde bloklanır
- Network policy → DNS/IP allowlist
- Critical path enforcement kernel-side (Ajanox process'i kapalı bile olsa)

### 4 use case

#### Use case 1: System-wide syscall audit

```c
// BCC tracepoint program
TRACEPOINT_PROBE(syscalls, sys_enter_execve) {
    struct event_t event = {};
    event.pid = bpf_get_current_pid_tgid();
    bpf_get_current_comm(&event.comm, sizeof(event.comm));
    bpf_probe_read_user_str(&event.filename, sizeof(event.filename),
                            (void *)args->filename);
    events.perf_submit(args, &event, sizeof(event));
    return 0;
}
```

Python tarafı:
```python
from bcc import BPF
b = BPF(text=ebpf_program)
b["events"].open_perf_buffer(lambda cpu, data, sz:
    ajanox.audit.log_kernel_event(b["events"].event(data)))
```

**Sonuç:** Her `execve()` syscall'ı Ajanox audit log'a → kullanıcı geçmişi
sistemi geneli gözlemlenebilir.

#### Use case 2: Network policy enforcement

Skill manifest:
```yaml
permissions: [network_read]
network:
  allowed_domains: [wttr.in, api.openweathermap.org]
```

Ajanox kernel'a XDP/TC program yükler — DNS sorgusu match etmiyorsa paket
DROP. Skill `network_read` izni var ama sadece izinli domain'lere.

```c
// XDP program (Network packet filtering)
SEC("xdp")
int filter_dns(struct xdp_md *ctx) {
    // DNS paketi parse et
    // Source: skill X process'i mi?
    // Dest: allowed_domains listesinde mi?
    // Match yoksa: XDP_DROP
    return XDP_PASS;
}
```

#### Use case 3: Critical path enforcement

`~/.ssh/id_rsa` okuma → kernel-level block. Ajanox process'i kapalı olsa
bile (yeni terminal'den yapılırsa) audit log + uyarı.

```c
// LSM hook
SEC("lsm/file_open")
int restrict_ssh_keys(struct file *file) {
    char path[256];
    bpf_d_path(&file->f_path, path, sizeof(path));
    if (strstr(path, "/.ssh/id_") && !is_authorized_process()) {
        return -EPERM;  // Block
    }
    return 0;
}
```

#### Use case 4: Process tree sandbox

Skill X'in spawn ettiği child process ağacı izole — `fork()` ve `clone()`
hook'larıyla.

```c
TRACEPOINT_PROBE(sched, sched_process_fork) {
    if (is_skill_process(args->parent_pid)) {
        // Mark child as part of skill sandbox
        // Sonra: bu child syscall'ları extra kısıtlanır
    }
    return 0;
}
```

### Teknik stack

| Katman | Teknoloji | Niçin |
|---|---|---|
| **Kernel** | Linux 5.10+ eBPF | Yerleşik, kararlı |
| **Compiler** | LLVM/Clang | BPF bytecode üretimi |
| **Tooling** | BCC (Python binding) | Hızlı geliştirme |
| **Production** | libbpf-rs (Rust) veya libbpf-go | Performans + CO-RE |
| **CO-RE** | BTF (BPF Type Format) | Kernel sürüm bağımsızlığı |

### Yeni Ajanox modülleri (v3.0)

```
src/ajanox/
├── kernel/                  ← YENİ
│   ├── __init__.py
│   ├── ebpf_loader.py       # eBPF programlarını yükle (root yetkisi)
│   ├── syscall_audit.py     # Use case 1 implementation
│   ├── network_policy.py    # Use case 2
│   ├── file_policy.py       # Use case 3
│   ├── process_sandbox.py   # Use case 4
│   └── programs/            # .c source files
│       ├── audit.c
│       ├── network.c
│       └── file.c
└── core/
    └── permissions.py       # Yeni permission: kernel_monitor
```

### Sınırlamalar (dürüst)

- **Sadece Linux** — macOS için Endpoint Security framework (Apple Silicon),
  Windows için ETW (Event Tracing for Windows)
- **Root yetkisi** — eBPF yüklemek için CAP_BPF + CAP_SYS_ADMIN
- **CO-RE gerekli** — eBPF programları kernel sürüm-bağımsız olsun
- **Performans dikkati** — XDP/TC her pakete eklenir, optimize edilmeli

### Cross-platform abstraction

```
core/kernel_policy.py (abstract interface)
   ↓
       ├── kernel/ebpf_*.py (Linux)
       ├── kernel/eslog_*.py (macOS Endpoint Security)
       └── kernel/etw_*.py (Windows, v4.0)
```

Aynı API, üç farklı platform implementation. Skill manifest aynı kalır.

### v3.0 timeline

```
v2.0 stable'dan sonra (yani Ay 10+'dan başlar):

Ay 11-12:  eBPF prototip (Use case 1: syscall audit)
Ay 13:     Use case 2 (network policy)
Ay 14:     Use case 3 (file enforcement)
Ay 15:     Use case 4 (process sandbox)
Ay 16:     Cross-platform abstraction (macOS Endpoint Security)
Ay 17:     Performance optimization
Ay 18:     v3.0 release
```

**~8 ay solo. 4-6 ay 3 kişilik takım.**

---

## Toplam Timeline

```
v0.5.0 (BUGÜN)
    │
    ├─── 0-6 ay: v0.6 → v1.0 (L3 stabil)
    │
    ├─── 6-16 ay: v2.0 (L2 Ubuntu remix)
    │           ├─ Ay 7: Modül A başlar
    │           ├─ Ay 8: Modül B
    │           ├─ ...
    │           └─ Ay 16: v2.0 stable
    │
    └─── 16-24 ay: v3.0 (eBPF)
                ├─ Ay 17: Syscall audit
                ├─ Ay 18: Network policy
                ├─ Ay 22: Cross-platform
                └─ Ay 24: v3.0 stable
```

**Toplam: 2 yıl solo, 1 yıl 3 kişilik takımla.**

---

## Takım yapısı önerisi (v2.0 itibarıyla)

Solo'dan profesyonele:

| Faz | Takım | Roller |
|---|---|---|
| **v0.5 - v1.0** | 1 kişi + AI | Özal (full-stack) |
| **v1.0 - v1.5** | 2-3 kişi | + Senior Python (core) + UI designer (brand) |
| **v2.0 - v2.5** | 5-8 kişi | + Distro engineer + DevOps + QA + Türkçe NLP araştırmacı |
| **v3.0+** | 10-15 kişi | + Kernel engineer + Security researcher + Topluluk yöneticisi |

**Finansman:**
- v1.5'a kadar: solo (kendi vakti)
- v2.0 başlangıcı: GitHub Sponsors / Open Collective ($2-5k/ay olası)
- v2.5+: Türkiye AI fonları (TÜBİTAK 1512, TEYDEB, Sanayi Bakanlığı)
- v3.0: Açık kaynak grant'ler (NLNet Foundation, OTF, Sovereign Tech Fund)

---

## Karar noktaları (şimdi düşünülmeli)

| Karar | Aciliyet | Yorumum |
|---|---|---|
| **Trademark "Ajanox"** | Orta | v1.0'dan önce TPE'ye başvur (~1500 TL, 18 ay) |
| **GitHub Organization** | Düşük | v2.0 öncesi kişisel'den `ajanox` org'a taşı |
| **Domain ajanox.com/dev** | Yüksek | Hemen al (~10 USD/yıl) — vizyon büyük, isim sahipliği kritik |
| **Telif Hakları (CLA)** | Orta | v1.5+ contributor CLA gerekli |
| **Yönetim modeli** | Düşük | Solo benevolent dictator → v3.0'da steering committee |

---

## Alternatif yollar (eğer L2 mümkün değilse)

Eğer 2 yıllık L2 yatırımı imkansızsa, daha küçük adımlar:

### Alternatif 1: "Ajanox for Ubuntu" snap
- ISO yerine snap package (`snap install ajanox`)
- Daha az customization ama daha az iş
- Ubuntu Store'da yayın

### Alternatif 2: Docker image
- `docker run ajanox/ajanox` → tam ortam ready
- Sanallaştırma → daha az native hissi
- Ama AI dev community için pratik

### Alternatif 3: Container OS (CoreOS modeli)
- Read-only base + Ajanox container layer
- Atomic updates
- Komplikedir ama "OS gibi hissedilen" katman

**Önerim: L2 (Ubuntu Remix) — uzun yolun en doğru yatırımı.** Diğerleri
ekosistem'i niş'leştirir.

---

## Sonuç

Bu yol haritası **emin değil, gerçekçi**. v2.0'a 12-18 ayda gitmek için:
1. v1.0 nu önce stabilize et (6 ay)
2. Brand + tasarımcı + finansman (paralel başlar)
3. Cubic ile ISO prototip (2 ay)
4. Toplulukla alpha → beta → stable (4 ay)

v3.0 = "kernel-derinliği policy" = **mevcut Linux eBPF altyapısı**, kernel
rewrite değil. Bu önemli — birçok proje burada kafa karıştırıyor.

**Asla:** L1 / L0 (sıfırdan kernel). ROI yok, Linus 35 yılını verdi, biz
o yola girmeyiz. Ajanox'un farkı AI ajan katmanı, kernel inovasyon değil.

---

**Sıradaki adım (somut):**
1. Bu doküman üzerinde refleksiyon (1 hafta)
2. v0.6 başlat (tool-call verification) — L3 stabilizasyon yolculuğu
3. Paralel: GitHub Sponsors aç, domain al, trademark araştır
4. 6 ay sonra: v2.0 ön çalışma başlar
