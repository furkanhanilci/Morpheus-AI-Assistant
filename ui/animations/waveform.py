"""
Waveform bars — alt kısımda yatay yerleştirilmiş ses çubukları.

Speaking sırasında rastgele yükseklikler alır.
Idle iken yumuşak sinüs dalga yapar.
Muted iken sabit kısa kırmızı çubuklar.
"""
from __future__ import annotations

import math
import random

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter

from ..themes import Theme


def draw(
    painter: QPainter,
    cx: float, cy: float,
    face_width: float,
    tick: int,             # sürekli artan zamanlayıcı (idle sinüs için)
    theme: Theme,
    speaking: bool = False,
    muted: bool = False,
    bar_count: int | None = None,
    bar_width: int = 8,
) -> None:
    """
    Waveform çubuklarını ekrana çiz.
    `cy + offset` yerleşimi: face'in alt kısmında ufak bir alan.
    """
    p = theme.palette
    n = bar_count or theme.animation.waveform_bars
    bw = bar_width
    wx0 = cx - (n * bw) / 2
    wy_top = cy + face_width * 0.40 + 30  # face'in altında

    for i in range(n):
        if muted:
            h = 2
            c = QColor(p.warning)
        elif speaking:
            h = random.randint(3, 20)
            c = QColor(p.primary if h > 12 else p.secondary_dim)
        else:
            h = int(3 + 2 * math.sin(tick * 0.09 + i * 0.6))
            c = QColor(p.secondary_dim)
        painter.fillRect(
            QRectF(wx0 + i * bw, wy_top + 20 - h, bw - 1, h),
            c,
        )
