"""
Global Signal Bus.

Tüm UI component'ları ve backend modülleri burada tanımlı signal'ları
emit edip dinler. Sıkı bağlılığı önler.

Kullanım:
    from ui.state.signals import bus

    # emit
    bus.log_appended.emit("SYS: ready")
    bus.state_changed.emit("LISTENING")
    bus.plan_step.emit({"step": 1, "tool": "web_search", "status": "running"})

    # listen
    bus.theme_changed.connect(self._on_theme_changed)

Kural: hiçbir component import yoluyla başka component'ı tetiklemez.
Hep signal üzerinden konuş.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """
    Merkezi event hub. Singleton olarak `bus` ile erişilir.

    Signal taksonomisi:
      • UI state    — speaking/listening/thinking gibi durum değişimleri
      • Logs        — log append, info/warn/err
      • Conversation — kullanıcı mesajı, asistan mesajı, regenerate isteği
      • Agent       — plan adımları, başla/bitti/iptal
      • Tools       — her tool çağrısı için lifecycle (start/finish/error)
      • Files       — dosya yükleme/kaldırma
      • Memory      — long_term.json değişiklikleri (UI'dan editlendiğinde)
      • Theme/perf  — tema veya performans mode değişimi
      • Input       — text command, PTT trigger, mute toggle
    """

    # ─── UI STATE ─────────────────────────────────────────────────────────────
    state_changed   = pyqtSignal(str)        # "LISTENING" | "SPEAKING" | "THINKING" | "MUTED" | "JACKING IN"
    speaking_set    = pyqtSignal(bool)       # True/False — HUD'a direkt geçer
    mute_set        = pyqtSignal(bool)

    # ─── LOG ──────────────────────────────────────────────────────────────────
    log_appended    = pyqtSignal(str)        # raw log line — tag log içinde inferred
    log_cleared     = pyqtSignal()

    # ─── CONVERSATION ─────────────────────────────────────────────────────────
    user_message    = pyqtSignal(str)        # kullanıcı bir şey söyledi/yazdı
    ai_message      = pyqtSignal(str)        # asistan cevap verdi (tam metin)
    ai_message_chunk = pyqtSignal(str)       # streaming için (opsiyonel)
    regenerate_requested = pyqtSignal(int)   # message index — Conversation view'dan

    # ─── AGENT PLAN ───────────────────────────────────────────────────────────
    plan_started    = pyqtSignal(dict)       # {"goal": str, "steps": [...]}
    plan_step       = pyqtSignal(dict)       # {"step": int, "tool": str, "status": "running|ok|err|pending", "duration_s": float, "result": str}
    plan_finished   = pyqtSignal(dict)       # {"success": bool, "summary": str}
    plan_cancel_requested = pyqtSignal()     # UI'dan iptal isteği

    # ─── TOOLS (atomic) ───────────────────────────────────────────────────────
    tool_started    = pyqtSignal(str, dict)  # (tool_name, params)
    tool_finished   = pyqtSignal(str, dict)  # (tool_name, {"duration_s": ..., "ok": bool, "result": ..., "error": ...})

    # ─── FILES ────────────────────────────────────────────────────────────────
    file_added      = pyqtSignal(str)        # path
    file_removed    = pyqtSignal(str)
    files_cleared   = pyqtSignal()

    # ─── MEMORY ───────────────────────────────────────────────────────────────
    memory_updated  = pyqtSignal(dict)       # full memory snapshot (UI editor'den)
    memory_entry_edited = pyqtSignal(str, str, str)  # (category, key, new_value)
    memory_entry_deleted = pyqtSignal(str, str)      # (category, key)

    # ─── THEME / PERF ─────────────────────────────────────────────────────────
    theme_changed   = pyqtSignal(object)     # Theme objesi
    perf_mode_changed = pyqtSignal(int)      # PerfLevel.value

    # ─── INPUT ────────────────────────────────────────────────────────────────
    text_command    = pyqtSignal(str)        # kullanıcı text input gönderdi
    ptt_pressed     = pyqtSignal()
    ptt_released    = pyqtSignal()
    listening_mode_changed = pyqtSignal(str) # "always" | "ptt" | "off"


# Tekil instance — modül seviyesinde, herkes burayı import eder.
bus = SignalBus()


__all__ = ["bus", "SignalBus"]
