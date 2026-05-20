"""
Buton primitive'leri.

Üç ana variant:
  • StyledButton  — temel buton, "tone" parametresi ile (primary/secondary/ghost/danger)
  • ToggleButton  — checked/unchecked durumlu buton (mute, fullscreen)
  • SegmentedControl — 2-N seçenekli segmented control (listening mode için)
"""
from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ..state import bus
from ..themes import Theme, get_theme


class StyledButton(QPushButton):
    """
    Tema-aware buton.

    tone:
      • "primary"   — hero rengi (idareli kullan: send, confirm)
      • "secondary" — varsayılan chrome (mavi)
      • "ghost"     — transparan, sadece border
      • "danger"    — kırmızı (delete, cancel)
    """

    VALID_TONES = ("primary", "secondary", "ghost", "danger")

    def __init__(
        self,
        text: str,
        tone: str = "secondary",
        height: int = 30,
        parent=None,
    ):
        super().__init__(text, parent)
        self._tone = tone if tone in self.VALID_TONES else "secondary"
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(height)

        bus.theme_changed.connect(self._on_theme)
        self._apply_theme(get_theme())

    def set_tone(self, tone: str) -> None:
        if tone in self.VALID_TONES:
            self._tone = tone
            self._apply_theme(get_theme())

    def _on_theme(self, theme: Theme) -> None:
        self._apply_theme(theme)

    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        # Tone → renk seti
        if self._tone == "primary":
            bg, fg, border = p.primary_ghost, p.primary, p.primary_dim
            hover_bg, hover_border = p.primary_ghost, p.primary
        elif self._tone == "danger":
            bg, fg, border = p.panel, p.warning, p.warning
            hover_bg, hover_border = p.panel_2, p.warning
        elif self._tone == "ghost":
            bg, fg, border = "transparent", p.text_dim, p.border
            hover_bg, hover_border = p.secondary_ghost, p.border_bright
        else:  # secondary
            bg, fg, border = p.panel, p.secondary, p.secondary_dim
            hover_bg, hover_border = p.secondary_ghost, p.secondary

        self.setFont(QFont(t.mono_family, t.size_sm, QFont.Weight.Bold))
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: {s.radius_sm}px;
                padding: 0 {s.md}px;
            }}
            QPushButton:hover {{
                background: {hover_bg};
                border: 1px solid {hover_border};
            }}
            QPushButton:pressed {{
                background: {p.panel_2};
            }}
            QPushButton:disabled {{
                color: {p.text_dim};
                border-color: {p.border_dim};
            }}
        """)


class ToggleButton(StyledButton):
    """
    İki-durumlu buton. checked=True → 'on' stili, False → 'off' stili.
    Kullanım yerleri: mute on/off, fullscreen on/off.
    """

    toggled_state = pyqtSignal(bool)

    def __init__(
        self,
        text_off: str,
        text_on: str,
        tone_off: str = "secondary",
        tone_on: str = "primary",
        checked: bool = False,
        height: int = 30,
        parent=None,
    ):
        self._text_off = text_off
        self._text_on  = text_on
        self._tone_off = tone_off
        self._tone_on  = tone_on
        self._checked  = checked

        initial_text = text_on if checked else text_off
        initial_tone = tone_on if checked else tone_off
        super().__init__(initial_text, tone=initial_tone, height=height, parent=parent)

        self.clicked.connect(self._toggle)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, value: bool) -> None:
        if value == self._checked:
            return
        self._checked = value
        self.setText(self._text_on if value else self._text_off)
        self.set_tone(self._tone_on if value else self._tone_off)
        self.toggled_state.emit(value)

    def _toggle(self) -> None:
        self.set_checked(not self._checked)


class SegmentedControl(QWidget):
    """
    2+ seçenekli segmented control.
    Listening mode (Always/PTT/Off) gibi yerlerde kullanılır.

    Kullanım:
        sc = SegmentedControl([("always","🔊"), ("ptt","🎙"), ("off","🔇")])
        sc.selected.connect(lambda key: print(key))
        sc.set_selected("ptt")
    """

    selected = pyqtSignal(str)  # seçilen key

    def __init__(
        self,
        segments: list[tuple[str, str]],  # [(key, label), ...]
        initial: str | None = None,
        height: int = 28,
        parent=None,
    ):
        super().__init__(parent)
        self._segments = segments
        self._buttons: dict[str, QPushButton] = {}
        self._selected: str = initial or segments[0][0]
        self._height = height

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        for key, label in segments:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(height)
            btn.clicked.connect(lambda _, k=key: self.set_selected(k))
            self._buttons[key] = btn
            lay.addWidget(btn, stretch=1)

        bus.theme_changed.connect(self._on_theme)
        self._apply_theme(get_theme())

    def selected_key(self) -> str:
        return self._selected

    def set_selected(self, key: str) -> None:
        if key not in self._buttons:
            return
        if key == self._selected:
            return
        self._selected = key
        self._apply_theme(get_theme())
        self.selected.emit(key)

    def _on_theme(self, theme: Theme) -> None:
        self._apply_theme(theme)

    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        sel_bg, sel_fg, sel_border = p.secondary_ghost, p.secondary, p.secondary
        un_bg, un_fg, un_border = p.panel, p.text_dim, p.border_dim

        for key, btn in self._buttons.items():
            is_sel = (key == self._selected)
            btn.setFont(QFont(t.mono_family, t.size_sm, QFont.Weight.Bold))
            if is_sel:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {sel_bg};
                        color: {sel_fg};
                        border: 1px solid {sel_border};
                        border-radius: {s.radius_sm}px;
                        padding: 0 {s.sm}px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {un_bg};
                        color: {un_fg};
                        border: 1px solid {un_border};
                        border-radius: {s.radius_sm}px;
                        padding: 0 {s.sm}px;
                    }}
                    QPushButton:hover {{
                        color: {p.text};
                        border: 1px solid {p.border_bright};
                    }}
                """)


__all__ = ["StyledButton", "ToggleButton", "SegmentedControl"]
