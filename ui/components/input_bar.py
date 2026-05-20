"""
InputBar — kullanıcının asistana yazılı komut girdiği bar.

Bileşenler (soldan sağa):
  [Listening mode segmented]  [Text input]  [Send ▸]

Listening mode segmented:
  🔊 Always   — sürekli dinle (default)
  🎙 PTT      — push-to-talk (SPACE basılı tut)
  🔇 Off      — sadece text

Davranış:
  • Enter → send
  • Send butonu → send
  • Hepsi bus.text_command emit eder
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from ..state import bus, state, ListeningMode
from ..themes import Theme, get_theme
from .buttons import SegmentedControl, StyledButton


class InputBar(QWidget):
    """
    Text + send + listening mode tek widget'ta.
    Backend (main.py) `bus.text_command.connect(...)` ile dinler.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # ─── Listening mode segmented ─────────────────────────────────────────
        self._listen_seg = SegmentedControl(
            segments=[
                ("always", "🔊"),
                ("ptt",    "🎙"),
                ("off",    "🔇"),
            ],
            initial=state.listening_mode.value,
            height=30,
        )
        self._listen_seg.setFixedWidth(120)
        self._listen_seg.selected.connect(self._on_listen_mode_changed)

        # ─── Text input ───────────────────────────────────────────────────────
        self._input = QLineEdit()
        self._input.setObjectName("InputBarText")
        self._input.setFixedHeight(30)
        self._input.returnPressed.connect(self._send)

        # ─── Send button ──────────────────────────────────────────────────────
        self._send_btn = StyledButton("▸", tone="primary", height=30)
        self._send_btn.setFixedWidth(36)
        self._send_btn.clicked.connect(self._send)

        # Layout
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._listen_seg)
        lay.addWidget(self._input, stretch=1)
        lay.addWidget(self._send_btn)

        bus.theme_changed.connect(self._apply_theme)
        bus.listening_mode_changed.connect(self._on_external_mode_change)
        self._apply_theme(get_theme())

    # ─── Behavior ─────────────────────────────────────────────────────────────
    def _send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        bus.user_message.emit(text)
        bus.text_command.emit(text)

    def _on_listen_mode_changed(self, key: str) -> None:
        # SegmentedControl seçimi → state update
        state.set_listening_mode(ListeningMode(key))

    def _on_external_mode_change(self, value: str) -> None:
        # State dışarıdan değişti (örn. settings paneli) → segmented'i senkronla
        self._listen_seg.set_selected(value)

    def set_focus(self) -> None:
        self._input.setFocus()

    # ─── Theming ──────────────────────────────────────────────────────────────
    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        self._input.setFont(QFont(t.mono_family, t.size_base))
        self._input.setPlaceholderText(self._placeholder_for(theme))
        self._input.setStyleSheet(f"""
            #InputBarText {{
                background: {p.dark};
                color: {p.text_strong};
                border: 1px solid {p.border};
                border-radius: {s.radius_sm}px;
                padding: 3px {s.md}px;
                selection-background-color: {p.secondary_ghost};
            }}
            #InputBarText:focus {{
                border: 1px solid {p.secondary};
            }}
        """)

    def _placeholder_for(self, theme: Theme) -> str:
        # Tema karakterine uygun placeholder
        if theme.slug == "morpheus":
            return "Wake Up, Neo…"
        if theme.slug == "mission_control":
            return "Mission command…"
        return "Type a message…"


__all__ = ["InputBar"]
