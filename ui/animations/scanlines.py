"""
CRT scanline overlay.

Görsel: 3-piksel aralıklı yatay çizgiler, çok soluk mavi.
Maliyet: çok düşük, her temada açılabilir.
"""
from __future__ import annotations

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QColor, QPainter, QPen

from ..themes import Theme


def draw(painter: QPainter, rect: QRect, theme: Theme, step: int = 3, alpha: int = 70) -> None:
    """Verilen dikdörtgen üzerine yatay scanline çizgileri ekler."""
    p = theme.palette
    # Çizgiler için "panel" rengini düşük opaklıkta kullan — temanın derinliğine uyar
    col = QColor(p.panel_2)
    col.setAlpha(alpha)
    painter.setPen(QPen(col, 1))
    w = rect.width()
    y0 = rect.top()
    y1 = rect.bottom()
    for y in range(y0, y1, step):
        painter.drawLine(rect.left(), y, rect.right(), y)
