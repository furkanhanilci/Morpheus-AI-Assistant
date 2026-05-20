"""
MorpheusUI — public API entry point.

main.py'nin gördüğü tek class. Eski ui.py'deki MorpheusUI ile aynı imzayı korur
(geriye uyumluluk), ama dahili olarak yeni mimariyi kullanır.

Eski API:
    ui = MorpheusUI("face.png")
    ui.set_state("LISTENING")
    ui.write_log("SYS: online")
    ui.muted             # property
    ui.current_file      # property
    ui.on_text_command   # callback setter
    ui.wait_for_api_key()
    ui.start_speaking() / stop_speaking()
    ui.root.mainloop()

Bunların hepsi PR-1 sonunda çalışır durumda — backend (main.py) hiçbir
değişiklik yapmadan yeni UI'a bağlanabilir.
"""
from __future__ import annotations

import sys
import time
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSlot
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow
from .state import bus, state, ConnState


class _RootShim:
    """tkinter.Tk uyumluluğu için shim — main.py `ui.root.mainloop()` çağırıyor."""
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


class _MainThreadMarshal(QObject):
    """
    Backend thread'inden gelen UI çağrılarını Qt main thread'e marshal eder.

    Bu sınıf main thread'de instantiate edilir (MorpheusUI.__init__ içinde).
    Public slot'lar @pyqtSlot ile işaretli — başka thread'den çağrılırsa
    Qt otomatik QueuedConnection ile main thread'e postlar.

    Qt'nin altın kuralı: widget metodları SADECE main thread'den çağrılır.
    Bu wrapper backend kodunun bu detayı bilmesine gerek bırakmaz.
    """

    @pyqtSlot(str)
    def set_state_slot(self, conn_state_str: str) -> None:
        try:
            cs = ConnState(conn_state_str)
            state.set_conn_state(cs)
        except ValueError:
            bus.log_appended.emit(f"SYS: unknown state '{conn_state_str}'")

    @pyqtSlot(bool)
    def set_speaking_slot(self, value: bool) -> None:
        state.set_speaking(value)

    @pyqtSlot(bool)
    def set_muted_slot(self, value: bool) -> None:
        state.set_muted(value)

    @pyqtSlot(str)
    def write_log_slot(self, text: str) -> None:
        bus.log_appended.emit(text)


class MorpheusUI:
    """
    Public UI handle. Backend (main.py) bu sınıfı tüketir.

    Tüm public method'lar thread-safe: backend hangi thread'den çağırırsa
    çağırsın, iş Qt main thread'inde yapılır.
    """

    def __init__(self, face_path: str = "", size: tuple[int, int] | None = None):
        self._face_path = face_path

        # Windows DPI awareness — Qt başlamadan önce set
        import os as _os
        import platform as _platform
        if _platform.system() == "Windows":
            # Qt'nin tekrar set etmeye çalışmasını engelle
            _os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
            try:
                import ctypes
                # PROCESS_PER_MONITOR_DPI_AWARE = 2
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

        # QApplication idempotent — birden fazla MorpheusUI olmaz ama
        # mevcut bir QApplication varsa onu kullan (test edilebilirlik için).
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")

        self._win = MainWindow(face_path=face_path)
        if size:
            self._win.resize(*size)
        self._win.show()

        # Main thread marshaller — backend thread'inden gelen çağrıları
        # Qt main thread'e queued connection ile postlar.
        # NOT: Bu obje main thread'de instantiate edildiği için
        # affinity'si main thread olur.
        self._marshal = _MainThreadMarshal()

        # tkinter uyumluluğu — main.py değişmeden çalışsın
        self.root = _RootShim(self._app)

        # text command callback — main.py'nin JarvisLive._on_text_command'ı
        self._on_text_command: Optional[Callable[[str], None]] = None

        # bus.text_command'a kendi callback dispatch'ini bağla
        bus.text_command.connect(self._dispatch_text_command)

    # ─── Backwards-compatible API ─────────────────────────────────────────────
    @property
    def muted(self) -> bool:
        return state.muted

    @muted.setter
    def muted(self, value: bool) -> None:
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self._marshal,
            "set_muted_slot",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(bool, bool(value)),
        )

    @property
    def current_file(self) -> str | None:
        files = state.files
        return files[-1] if files else None

    @property
    def on_text_command(self) -> Optional[Callable[[str], None]]:
        return self._on_text_command

    @on_text_command.setter
    def on_text_command(self, cb: Optional[Callable[[str], None]]) -> None:
        self._on_text_command = cb

    def _dispatch_text_command(self, text: str) -> None:
        """bus.text_command → external callback dispatcher."""
        if self._on_text_command:
            try:
                self._on_text_command(text)
            except Exception as e:
                print(f"[MorpheusUI] text_command callback error: {e}")

    def set_state(self, conn_state: str) -> None:
        """
        Eski API: ui.set_state("LISTENING").
        Thread-safe: arka plan thread'inden çağrılırsa main thread'e marshal edilir.
        """
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self._marshal,
            "set_state_slot",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, conn_state),
        )

    def write_log(self, text: str) -> None:
        """Thread-safe log write."""
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self._marshal,
            "write_log_slot",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, str(text)),
        )

    def wait_for_api_key(self) -> None:
        """
        Eski API: API key onboarding tamamlanana kadar blokla.
        BU METOD BACKEND THREAD'İNDEN ÇAĞRILIR — show_setup_blocking de
        thread-safe olarak invoke edilir.
        """
        from PyQt6.QtCore import QMetaObject
        import time as _t
        from pathlib import Path
        import sys as _sys

        # Config path — main.py'nin yanındaki config/api_keys.json
        # __file__ yöntemi kullanıcı terminalinin nerede açıldığından bağımsız.
        if getattr(_sys, "frozen", False):
            base = Path(_sys.executable).parent
        else:
            # ui/app.py → parent.parent = project root
            base = Path(__file__).resolve().parent.parent
        cfg = base / "config" / "api_keys.json"

        # Zaten varsa hemen dön — overlay'i göstermeye gerek yok
        if cfg.exists():
            try:
                import json as _json
                data = _json.loads(cfg.read_text(encoding="utf-8"))
                if data.get("gemini_api_key") and len(data["gemini_api_key"]) > 15:
                    print("[MorpheusUI] API key already configured, skipping setup.")
                    return
            except Exception:
                pass

        # Setup overlay'i main thread'de göster
        print("[MorpheusUI] No API key found, showing setup overlay...")
        QTimer.singleShot(0, self._win.show_setup_blocking)

        # Polling — config dosyası geçerli hale gelene kadar bekle
        # (en fazla saatlerce — kullanıcı bilgisayarını kapatabilir)
        import json as _json
        while True:
            _t.sleep(0.5)
            if cfg.exists():
                try:
                    data = _json.loads(cfg.read_text(encoding="utf-8"))
                    if data.get("gemini_api_key") and len(data["gemini_api_key"]) > 15:
                        break
                except Exception:
                    continue
        _t.sleep(0.3)  # son yazımın bitmesi için
        print("[MorpheusUI] API key configured, starting backend.")

    def start_speaking(self) -> None:
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self._marshal,
            "set_speaking_slot",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(bool, True),
        )

    def stop_speaking(self) -> None:
        if state.muted:
            return
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self._marshal,
            "set_speaking_slot",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(bool, False),
        )

    # ─── Yeni API (PR-1) — tema kontrolü ──────────────────────────────────────
    def set_theme(self, slug: str) -> None:
        """Tema değiştir. slug: 'morpheus' | 'mission_control' | 'minimal'."""
        state.set_theme(slug)


# Geriye uyumluluk: eski kod `JarvisUI` ismini de bekleyebilir.
JarvisUI = MorpheusUI


__all__ = ["MorpheusUI", "JarvisUI"]
