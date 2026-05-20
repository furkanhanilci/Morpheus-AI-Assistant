"""
MetricBar — küçük yatay metrik göstergesi.

Etkili olduğu yerler: sidebar CPU/MEM/NET/GPU/TMP göstergeleri.

Görsel:
    ┌─────────────────────────┐
    │ CPU              42%    │
    │ ███████░░░░░░░░░░░░░    │
    └─────────────────────────┘

Eski ui.py'deki MetricBar mantığının tema-aware refactor'u:
  • Renkler aktif temadan alınır
  • Eşik değerleri (warning=85%, caution=65%) sabit kalır
  • Color hint olarak "tone" alır (primary/secondary/warning/custom)
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ..state import bus
from ..themes import Theme, get_theme


def _qcol(hex_str: str, alpha: int = 255) -> QColor:
    c = QColor(hex_str)
    c.setAlpha(alpha)
    return c


class MetricBar(QWidget):
    """
    Etiket + sayısal değer + ince doluluk çubuğu.

    Args:
        label: sol üstte gösterilen etiket (örn "CPU")
        tone:  default bar rengi anahtarı — "primary"|"secondary"|"accent"|"warning"
        custom_color: doğrudan hex kod (tone'u override eder)

    Method:
        set_value(pct: float, text: str)  → 0-100 doluluk + sağ üstte gösterilecek metin
    """

    THRESHOLD_WARN    = 85.0   # %85+ kırmızı
    THRESHOLD_CAUTION = 65.0   # %65+ vurgulu (primary)

    def __init__(
        self,
        label: str,
        tone: str = "secondary",
        custom_color: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._label = label
        self._tone = tone
        self._custom_color = custom_color
        self._value = 0.0
        self._text  = "--"
        self.setFixedHeight(38)
        self.setMinimumWidth(80)

        bus.theme_changed.connect(self._on_theme)
        # Tema değiştiğinde paintEvent zaten yenilenir, ama force update
        # için update() çağırmamız gerekiyor.

    def set_value(self, pct: float, text: str) -> None:
        self._value = max(0.0, min(100.0, pct))
        self._text  = text
        self.update()

    def _on_theme(self, _theme: Theme) -> None:
        self.update()

    def _resolve_bar_color(self, theme: Theme) -> QColor:
        """Doluluk değerine ve tema'ya göre bar rengini seç."""
        p = theme.palette
        if self._value > self.THRESHOLD_WARN:
            return _qcol(p.warning)
        if self._value > self.THRESHOLD_CAUTION:
            return _qcol(p.primary)

        if self._custom_color:
            return _qcol(self._custom_color)

        color_attr = self._tone
        return _qcol(getattr(p, color_attr, p.secondary))

    def paintEvent(self, _evt) -> None:
        theme = get_theme()
        p_obj = theme.palette
        t = theme.typography
        s = theme.spacing

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Background card
        painter.setBrush(QBrush(_qcol(p_obj.panel_2)))
        painter.setPen(QPen(_qcol(p_obj.border_dim), 1))
        painter.drawRoundedRect(
            QRectF(1, 1, W - 2, H - 2),
            s.radius_md, s.radius_md,
        )

        # Bar geometry — alt kısım
        bar_h = 4
        bar_y = H - bar_h - 5
        bar_x = s.md
        bar_w = W - 2 * s.md
        fill_w = int(bar_w * self._value / 100)

        # Bar track
        painter.setBrush(QBrush(_qcol(p_obj.bg)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2, 2)

        # Bar fill
        if fill_w > 0:
            painter.setBrush(QBrush(self._resolve_bar_color(theme)))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2, 2)

        # Label (sol üst)
        painter.setFont(QFont(t.mono_family, t.size_xs, QFont.Weight.Bold))
        painter.setPen(QPen(_qcol(p_obj.text_dim), 1))
        painter.drawText(
            QRectF(s.lg, 5, W - 2 * s.lg, 14),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._label,
        )

        # Value text (sağ üst) — bar rengiyle vurgulu
        value_col = self._resolve_bar_color(theme) if self._text != "--" else _qcol(p_obj.text_dim)
        painter.setFont(QFont(t.mono_family, t.size_base, QFont.Weight.Bold))
        painter.setPen(QPen(value_col, 1))
        painter.drawText(
            QRectF(0, 4, W - s.md, 16),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            self._text,
        )


__all__ = ["MetricBar"]
