# MARK XXXIX — UI v2 Migration Guide

PR-1 → PR-8 boyunca yeni `ui/` paketi eski `ui.py`'nin yerini aldı.
Bu rehber projeyi nasıl entegre edeceğini ve eski sürümden nasıl
geçeceğini anlatır.

## 1. Dosya yapısı (önce / sonra)

**Önce:**
```
Mark-XXXIX/
├── ui.py                ← 2030 satır, tek dosya
├── main.py
├── agent/
├── actions/
├── memory/
└── config/
```

**Sonra:**
```
Mark-XXXIX/
├── ui/                  ← yeni paket
│   ├── __init__.py      (public API: MorpheusUI)
│   ├── app.py           (entry sınıfı)
│   ├── main_window.py   (layout shell)
│   ├── themes/          (Morpheus / Mission Control / Minimal)
│   ├── components/      (button, panel, drop_zone, tab_bar, ...)
│   ├── views/           (HUD canvas, conversation, plan, tools, memory, ...)
│   ├── animations/      (matrix_rain, halo, rings, particles, ...)
│   ├── overlays/        (setup_overlay)
│   ├── state/           (signals, ui_state, sys_metrics)
│   └── bridge/          (backend → UI emit yardımcıları)
├── ui_legacy.py         ← eski ui.py yedeği (ileride silinir)
├── main.py
├── agent/
├── actions/
├── memory/
├── config/
└── patches/             ← opsiyonel backend patch'leri
```

## 2. Dakika dakika kurulum

```bash
# 1. Yedek al
mv ui.py ui_legacy.py

# 2. Yeni ui/ paketini yerleştir
cp -r path/to/pr8/ui ./

# 3. main.py import kontrol
# Eski: from ui import JarvisUI
# Yeni: from ui import MorpheusUI   (JarvisUI alias hâlâ çalışır)

# 4. requirements.txt'te PyQt6 ve psutil zaten vardı, yeni bağımlılık yok

# 5. Test
python main.py
```

İlk çalışmada API key yoksa **SetupOverlay** otomatik açılır.

## 3. main.py'de değişen şey VAR mı?

**Hayır.** Backwards-compatible. Eski API'nin tamamı korunuyor:

```python
ui = MorpheusUI("face.png")     # ✅
ui.set_state("LISTENING")       # ✅
ui.write_log("SYS: ready")      # ✅
ui.start_speaking()             # ✅
ui.stop_speaking()              # ✅
ui.muted = True                 # ✅
ui.current_file                 # ✅
ui.on_text_command = cb         # ✅
ui.wait_for_api_key()           # ✅ artık SetupOverlay tetikler
ui.root.mainloop()              # ✅
```

`from ui import JarvisUI` da çalışır (alias) — ama yeni kodlarda `MorpheusUI`
kullanmanı öneririm.

## 4. Yeni özelliklerden yararlanmak için (opsiyonel)

### Theme switching
```python
ui.set_theme("morpheus")          # default
ui.set_theme("mission_control")
ui.set_theme("minimal")
```

### Conversation thread
Mevcut `main.py` zaten user mesajlarını text command olarak alıyor.
Asistanın cevabını UI'a göndermek için:

```python
from ui.state import bus

# Asistan bir şey söylediğinde:
bus.ai_message.emit(transcript_text)
```

Conversation tab otomatik dolar. Hiç emit etmesen de UI sorunsuz çalışır.

### Agent plan + tool feed
`patches/01_executor_bridge.md` dosyasında ne yapacağın yazılı.
Uygulamazsan iki tab boş kalır ama UI fonksiyonel.

### PTT
`patches/02_main_ptt_wiring.md` dosyasında. UI tarafı zaten hazır,
backend tarafında mic gate'i eklemen gerekiyor.

### Memory inspector
Otomatik çalışır — `memory/long_term.json`'u doğrudan okur/yazar.
Backend `bus.memory_updated.emit(snapshot)` çağırırsa UI tazelenir.

## 5. Eski ui.py ne zaman silinir?

**Şimdi silmiyoruz.** Bir-iki hafta `ui_legacy.py` olarak kalsın, sen
yeni UI'yi gerçek kullanım altında test et. Sorun çıkarsa kolayca
geri dönebilirsin:

```python
# Acil rollback (main.py içinde):
from ui_legacy import JarvisUI  # eski ui.py
```

Hiç bir sorun yoksa, sonra sil:
```bash
rm ui_legacy.py
```

## 6. Versiyon tutarsızlıkları

PR-1'deki proje analizinde fark ettiğimiz "MARK XXV → XXXIX" tutarsızlıkları:

### setup.py
```diff
-     name='mark25',
-     description='MARK XXV',
+     name='mark39',
+     description='MARK XXXIX',
```

### core/prompt.txt
```diff
- You are MARK XXV, ...
+ You are MARK XXXIX, ...
```

### agent/error_handler.py
```diff
- "You are the error recovery module of MARK XXV AI assistant."
+ "You are the error recovery module of MARK XXXIX AI assistant."
```

## 7. .gitignore

API key'in repo'da olmaması için:

```gitignore
# Local credentials
config/api_keys.json

# Memory (kişisel)
memory/long_term.json

# Python
__pycache__/
*.pyc
.venv/

# Qt offscreen / pytest artıkları
.pytest_cache/
htmlcov/

# IDE
.vscode/
.idea/
```

İdeal: `config/api_keys.example.json` da commit et, gerçek dosya gitignore'da.

## 8. Test checklist

Yeni UI'yi kabul etmeden önce:

- [ ] `python main.py` çalışıyor, pencere açılıyor
- [ ] API key yokken SetupOverlay çıkıyor
- [ ] API key girince modal kapanıyor, ana ekran açılıyor
- [ ] Sol panel CPU/MEM/NET değerleri canlı
- [ ] Merkez HUD: rain + halo + rings + waveform animasyonlu
- [ ] Asistan konuşmaya başlayınca halo parlıyor, particles fışkırıyor
- [ ] Mute (F4) → tüm canlı renkler kırmızı, mic durur
- [ ] Settings → Theme'i Mission Control'e değiştir → tüm UI amber
- [ ] Settings → Theme'i Minimal'e değiştir → sade görünüm
- [ ] Settings → Performance'ı Low'a düşür → animasyon yavaşlar, CPU düşer
- [ ] Settings → Input → PTT seç → SPACE basılı tutmadan mic gelmez
- [ ] Memory tab → entry'lerini gör, bir tanesini edit et → disk'e yazıldı mı
- [ ] Files tab → bir dosya drop'la → görünür, ✕ ile sil
- [ ] Chat tab → bir text gönder → user kartı belirir, asistan cevap verirse AI kartı
- [ ] Plan tab → agent_task tetikle → adımlar canlı dolacak (patch uygulandıysa)
- [ ] Tools tab → her tool çağrısı timestamp'le görünüyor (patch uygulandıysa)
- [ ] Pencereyi minimize et → bir-iki saniye sonra animasyonlar yavaşlar
- [ ] Geri büyüt → animasyonlar normale döner

## 9. Sorun çıkarsa

`ui_legacy.py` ile karşılaştır:

```bash
# Hangi davranış eski'de neydi?
git log --oneline ui_legacy.py | head -5
```

veya tarayıcıda 8 PR README'sini oku (`pr1/README.md`, `pr2/README.md`, ...).
Her PR ne ekledi, nasıl test ettim, ne kırılma riski var — hepsi orada.
