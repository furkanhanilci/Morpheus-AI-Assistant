"""
TabBar — sağ dock için sekme barı.

Görsel:
    ┌───────────────────────────────┐
    │ [💬] [🧩] [⚡] [🧠] [📂] [⚙] │
    └───────────────────────────────┘

Aktif sekme alt çizgi + bright color, diğerleri dim.
İkon + (opsiyonel) küçük badge (Plan tab'ı için "running" göstergesi).
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ..state import bus
from ..themes import Theme, get_theme


class TabBar(QWidget):
    """
    Sekme barı.

    Kullanım:
        bar = TabBar([
            ("chat", "💬", "Chat"),
            ("plan", "🧩", "Plan"),
            ...
        ])
        bar.tab_changed.connect(lambda key: ...)
    """

    tab_changed = pyqtSignal(str)  # active tab key

    def __init__(self, tabs: list[tuple[str, str, str]],
                 initial: str | None = None, parent: Optional[QWidget] = None):
        """
        tabs: [(key, icon, tooltip), ...]
        """
        super().__init__(parent)
        self.setObjectName("TabBar")
        self._tabs = tabs
        self._active: str = initial or tabs[0][0]
        self._buttons: dict[str, QPushButton] = {}
        self._badges: dict[str, bool] = {key: False for key, _, _ in tabs}

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        for key, icon, tooltip in tabs:
            btn = QPushButton(icon)
            btn.setObjectName(f"Tab_{key}")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setToolTip(tooltip)
            btn.setFixedHeight(38)
            btn.clicked.connect(lambda _, k=key: self.set_active(k))
            self._buttons[key] = btn
            lay.addWidget(btn, stretch=1)

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def active(self) -> str:
        return self._active

    def set_active(self, key: str) -> None:
        if key not in self._buttons or key == self._active:
            return
        self._active = key
        self._apply_theme(get_theme())
        self.tab_changed.emit(key)

    def set_badge(self, key: str, value: bool) -> None:
        """Sekme üzerinde ufak nokta — bir şey 'çalışıyor' göstergesi."""
        if key not in self._badges:
            return
        self._badges[key] = value
        self._apply_theme(get_theme())

    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        for key, btn in self._buttons.items():
            is_active = (key == self._active)
            has_badge = self._badges.get(key, False)

            # Aktif tab: bright color + alt bar
            # Pasif:   text_dim + transparent bg
            # Badge:   tab içeriğinde küçük noktayla
            color = p.primary if is_active else p.text_dim
            bg = p.panel_2 if is_active else "transparent"
            border_bottom = f"2px solid {p.primary}" if is_active else f"2px solid transparent"

            # Badge — basit text suffix
            icon = btn.text().split("●")[0].strip()  # önceki badge'i temizle
            if has_badge:
                display = f"{icon}●"
            else:
                display = icon

            btn.setText(display)
            btn.setFont(QFont(t.sans_family, t.size_lg))
            btn.setStyleSheet(f"""
                QPushButton#{btn.objectName()} {{
                    background: {bg};
                    color: {color};
                    border: none;
                    border-bottom: {border_bottom};
                    padding: 0;
                }}
                QPushButton#{btn.objectName()}:hover {{
                    color: {p.text};
                    background: {p.secondary_ghost};
                }}
            """)

        # Container — alt çizgi
        self.setStyleSheet(f"""
            #TabBar {{
                background: {p.dark};
                border-bottom: 1px solid {p.border};
            }}
        """)


__all__ = ["TabBar"]
