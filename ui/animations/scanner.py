"""
Scanner arc — dış kabuk üzerinde gezinen yay.

İki katmanlı: primary (yeşil) ana arc + secondary (mavi) ters yönlü ikinci arc.
Speaking sırasında daha hızlı döner ve daha geniş extension açar.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from ..themes import Theme


def draw(
    painter: QPainter,
    cx: float, cy: float,
    face_width: float,
    scan_primary: float,    # primary arc başlangıç açısı
    scan_secondary: float,  # secondary arc başlangıç açısı
    halo_strength: float,
    theme: Theme,
    speaking: bool = False,
    muted: bool = False,
) -> None:
    p = theme.palette
    sr = face_width * 0.50
    sa = min(255, int(halo_strength * 1.5))
    extension_deg = 75 if speaking else 44

    rect = QRectF(cx - sr, cy - sr, sr * 2, sr * 2)

    primary_col_hex = p.warning if muted else p.primary
    c1 = QColor(primary_col_hex); c1.setAlpha(sa)
    painter.setPen(QPen(c1, 2.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(rect, int(scan_primary * 16), int(extension_deg * 16))

    c2 = QColor(p.secondary); c2.setAlpha(sa // 2)
    painter.setPen(QPen(c2, 1.5))
    painter.drawArc(rect, int(scan_secondary * 16), int(extension_deg * 16))
