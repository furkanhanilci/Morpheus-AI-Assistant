"""
SetupOverlay — API key onboarding modal.

Davranış:
  • API key dosyası yoksa veya boşsa show() ile blok olur
  • Kullanıcı key girip Save dediğinde dosyaya yazar ve overlay kapanır
  • wait_for_key() çağıran iş parçacığını (genelde main) bloklar

main.py'nin eski API'sını koruyalım:
    ui.wait_for_api_key()   # API key girilene kadar bekler
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QEventLoop, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget,
)

from ..components import StyledButton
from ..state import bus
from ..themes import Theme, get_theme


# config/api_keys.json yolu
_API_KEY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "config", "api_keys.json"
)


def _read_existing_key() -> str:
    try:
        p = Path(_API_KEY_PATH).resolve()
        if p.exists():
            with open(p) as f:
                data = json.load(f)
            # Backwards compat — eski sürüm büyük harf kullanıyordu
            return data.get("gemini_api_key", "") or data.get("GEMINI_API_KEY", "")
    except Exception:
        pass
    return ""


def _save_key(key: str) -> bool:
    try:
        p = Path(_API_KEY_PATH).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if p.exists():
            try:
                with open(p) as f:
                    data = json.load(f)
            except Exception:
                pass
        # KÜÇÜK HARF — backend ve actions/ bunu okuyor
        data["gemini_api_key"] = key
        # Eski büyük harf alanı varsa temizle (karışıklığı önle)
        data.pop("GEMINI_API_KEY", None)
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[SetupOverlay] save error: {e}")
        return False


class SetupOverlay(QWidget):
    """
    Parent window üzerinde tam ekran modal.
    Arka plan blur yerine semi-transparent karartma.
    """

    def __init__(self, parent: QWidget):
        # Eğer parent bir QMainWindow ise, central widget'ı parent yap.
        # Aksi halde overlay central widget'ın arkasında kalır.
        from PyQt6.QtWidgets import QMainWindow
        if isinstance(parent, QMainWindow):
            cw = parent.centralWidget()
            if cw is not None:
                parent = cw
        super().__init__(parent)
        self.setObjectName("SetupOverlay")
        # Parent'ın tam boyutunda
        self.resize(parent.size())
        # Parent resize'ında biz de büyürüz
        parent.installEventFilter(self)

        self._build_ui()
        self._loop: Optional[QEventLoop] = None

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def _build_ui(self):
        # Ana wrapper — tam alanı kaplar, ortada bir card
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()

        center_row = QHBoxLayout()
        center_row.addStretch()

        self._card = QWidget()
        self._card.setObjectName("SetupCard")
        self._card.setFixedWidth(440)
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(24, 24, 24, 24)
        card_lay.setSpacing(12)

        self._title = QLabel("◈  JACK IN")
        self._title.setObjectName("SetupTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lay.addWidget(self._title)

        self._desc = QLabel(
            "MARK XXXIX needs a Gemini API key to connect.\n"
            "Get one from https://aistudio.google.com/apikey"
        )
        self._desc.setObjectName("SetupDescription")
        self._desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc.setWordWrap(True)
        card_lay.addWidget(self._desc)

        self._input = QLineEdit()
        self._input.setObjectName("SetupInput")
        self._input.setPlaceholderText("AIzaSy...")
        self._input.setEchoMode(QLineEdit.EchoMode.Password)
        self._input.setText(_read_existing_key())
        self._input.returnPressed.connect(self._submit)
        card_lay.addWidget(self._input)

        # Action row
        row = QHBoxLayout()
        row.setSpacing(8)

        self._show_btn = StyledButton("👁", tone="ghost", height=32)
        self._show_btn.setFixedWidth(40)
        self._show_btn.clicked.connect(self._toggle_visibility)
        row.addWidget(self._show_btn)

        row.addStretch()

        self._submit_btn = StyledButton("CONNECT  →", tone="primary", height=32)
        self._submit_btn.clicked.connect(self._submit)
        row.addWidget(self._submit_btn)
        card_lay.addLayout(row)

        self._error_label = QLabel("")
        self._error_label.setObjectName("SetupError")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        card_lay.addWidget(self._error_label)

        center_row.addWidget(self._card)
        center_row.addStretch()
        outer.addLayout(center_row)
        outer.addStretch()

    def _toggle_visibility(self):
        if self._input.echoMode() == QLineEdit.EchoMode.Password:
            self._input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_btn.setText("🙈")
        else:
            self._input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_btn.setText("👁")

    def _submit(self):
        key = self._input.text().strip()
        if not key:
            self._error_label.setText("✗ Key cannot be empty")
            return
        if len(key) < 20:
            self._error_label.setText("✗ Key looks too short")
            return
        if not _save_key(key):
            self._error_label.setText("✗ Could not write config file")
            return

        bus.log_appended.emit("SYS: API key configured")
        self._close()

    def _close(self):
        self.hide()
        if self._loop and self._loop.isRunning():
            self._loop.quit()

    def wait_for_key(self):
        """API key girilene kadar blokla."""
        existing = _read_existing_key()
        if existing and len(existing) >= 20:
            return  # zaten var
        self._input.setFocus()
        self.show()
        self.raise_()
        self._loop = QEventLoop()
        self._loop.exec()

    def eventFilter(self, obj, event):
        # Parent resize → biz de yeniden boyutlan
        from PyQt6.QtCore import QEvent
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self.resize(self.parent().size())
        return super().eventFilter(obj, event)

    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        self._title.setFont(QFont(t.mono_family, t.size_xl, QFont.Weight.Bold))
        self._desc.setFont(QFont(t.mono_family, t.size_sm))
        self._input.setFont(QFont(t.mono_family, t.size_base))
        self._error_label.setFont(QFont(t.mono_family, t.size_xs))

        # Semi-transparent karartma + ortadaki card
        self.setStyleSheet(f"""
            #SetupOverlay {{
                background: rgba(2, 6, 16, 230);
            }}
            #SetupCard {{
                background: {p.panel};
                border: 1px solid {p.primary_dim};
                border-radius: {s.radius_lg}px;
            }}
            #SetupTitle {{
                color: {p.primary};
                background: transparent;
                border: none;
                padding: 4px 0 8px 0;
            }}
            #SetupDescription {{
                color: {p.text_dim};
                background: transparent;
                border: none;
            }}
            #SetupInput {{
                background: {p.dark};
                color: {p.text_strong};
                border: 1px solid {p.border};
                border-radius: {s.radius_sm}px;
                padding: 6px {s.md}px;
                min-height: 24px;
            }}
            #SetupInput:focus {{ border: 1px solid {p.primary}; }}
            #SetupError {{
                color: {p.warning};
                background: transparent;
                border: none;
                min-height: 14px;
            }}
        """)


__all__ = ["SetupOverlay"]
