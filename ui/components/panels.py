"""
Yeniden kullanılabilir panel primitive'leri.

Hepsi tema-aware: SignalBus.theme_changed'i dinler, stylesheet'ini yeniler.
Hardcoded renk yok — her zaman aktif tema üzerinden okur.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from ..state import bus
from ..themes import Theme, get_theme


class _ThemedWidget(QWidget):
    """
    Tema değişimini otomatik takip eden base class.
    Alt sınıflar `_apply_theme(theme)` override eder.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        bus.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme: Theme) -> None:
        try:
            self._apply_theme(theme)
        except Exception as e:
            print(f"[{type(self).__name__}] theme apply error: {e}")

    def _apply_theme(self, theme: Theme) -> None:
        """Alt sınıflar override eder."""
        pass


class SectionHeader(QLabel):
    """
    `▸ TITLE` stilindeki bölüm başlığı.
    Sidebar/right dock'ta her grup başlığında kullanılır.
    """
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._raw_text = text
        self.setObjectName("SectionHeader")
        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def set_text(self, text: str) -> None:
        self._raw_text = text
        th = get_theme()
        self.setText(f"▸ {text}")

    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        self.setText(f"▸ {self._raw_text}")
        self.setFont(QFont(t.mono_family, t.size_xs, QFont.Weight.Bold))
        self.setStyleSheet(
            f"color: {p.secondary}; "
            f"background: transparent; "
            f"border-bottom: 1px solid {p.border}; "
            f"padding-bottom: {theme.spacing.sm}px;"
        )


class Divider(QFrame):
    """İnce yatay ayraç. Tema border rengini kullanır."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        self.setStyleSheet(
            f"background: {p.border}; "
            f"color: {p.border}; "
            f"border: none; "
            f"margin: {theme.spacing.xs}px 0;"
        )


class Panel(_ThemedWidget):
    """
    İçerik kutusu — border + radius + tema-aware arka plan.
    Header parametresi verilirse üstte küçük başlık çıkar.

    Kullanım:
        panel = Panel(title="STATUS")
        panel.add_widget(some_label)
    """
    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)

        self._title_label: QLabel | None = None
        if title:
            self._title_label = QLabel(title)
            self._title_label.setObjectName("PanelTitle")
            self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._lay.addWidget(self._title_label)

        # Content container — kullanıcı bunun içine ekleme yapacak
        self._content = QWidget()
        self._content.setObjectName("PanelContent")
        self._content_lay = QVBoxLayout(self._content)
        self._lay.addWidget(self._content, stretch=1)

        self._apply_theme(get_theme())

    def add_widget(self, w: QWidget) -> None:
        self._content_lay.addWidget(w)

    def add_layout(self, layout) -> None:
        self._content_lay.addLayout(layout)

    def content_layout(self) -> QVBoxLayout:
        return self._content_lay

    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        # Content margin tema spacing'den
        self._content_lay.setContentsMargins(s.md, s.md, s.md, s.md)
        self._content_lay.setSpacing(s.sm)

        self.setStyleSheet(f"""
            #Panel {{
                background: {p.panel_2};
                border: 1px solid {p.border};
                border-radius: {s.radius_md}px;
            }}
            #PanelTitle {{
                color: {p.text_dim};
                background: {p.panel};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
                font-weight: bold;
                padding: {s.sm}px {s.md}px;
                border-bottom: 1px solid {p.border_dim};
                border-top-left-radius: {s.radius_md}px;
                border-top-right-radius: {s.radius_md}px;
            }}
            #PanelContent {{
                background: transparent;
            }}
        """)


class StatusPill(_ThemedWidget):
    """
    Küçük durum etiketi — örn. "MIND CORE\nONLINE".
    Renk argümanı: "primary" | "secondary" | "accent" | "text_dim"

    Kullanım:
        pill = StatusPill("MIND CORE\nONLINE", tone="primary")
    """
    TONE_MAP = {
        "primary":   "primary",
        "secondary": "secondary",
        "accent":    "accent",
        "warning":   "warning",
        "text_dim":  "text_dim",
        "muted":     "text_dim",
    }

    def __init__(self, text: str, tone: str = "secondary", parent=None):
        super().__init__(parent)
        self.setObjectName("StatusPill")
        self._tone = self.TONE_MAP.get(tone, "secondary")

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)

        self._label = QLabel(text)
        self._label.setObjectName("StatusPillLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._lay.addWidget(self._label)

        self._apply_theme(get_theme())

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def set_tone(self, tone: str) -> None:
        self._tone = self.TONE_MAP.get(tone, "secondary")
        self._apply_theme(get_theme())

    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        color_attr = self._tone
        color = getattr(p, color_attr, p.secondary)

        self.setStyleSheet(f"""
            #StatusPill {{
                background: {p.panel_2};
                border: 1px solid {p.border_dim};
                border-radius: {s.radius_sm}px;
            }}
            #StatusPillLabel {{
                color: {color};
                background: transparent;
                border: none;
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
                font-weight: bold;
                padding: {s.sm}px {s.xs}px;
            }}
        """)


__all__ = ["Panel", "SectionHeader", "Divider", "StatusPill"]
