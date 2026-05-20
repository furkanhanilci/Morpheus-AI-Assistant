"""
Dönen halkalar (spinning rings).

Face'i çevreleyen 3 ayrı halka — her biri farklı yarıçap, kalınlık ve arc uzunluğunda.
Renk sırası: outer = primary (yeşil), middle = secondary (mavi), inner = primary.

Tema'nın `animation.rings_count` parametresi 0-3 arası — kaç halka çizileceğini belirler.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from ..themes import Theme


# Halka tanımları: (r_fraction, pen_width, arc_length_deg, gap_deg)
_RING_SPECS = [
    (0.48, 3, 115, 78),   # 0: outer
    (0.40, 2,  78, 55),   # 1: middle
    (0.32, 1,  56, 40),   # 2: inner
]


def draw(
    painter: QPainter,
    cx: float, cy: float,
    face_width: float,         # min(W, H) — boyutlandırma için
    ring_angles: list[float],  # her halkanın anki başlangıç açısı, len >= rings_count
    halo_strength: float,      # halo ile senkron
    theme: Theme,
    muted: bool = False,
) -> None:
    """
    Tema'nın istediği sayıda halka çizer.
    rings_count = 0 → hiç çizmez.
    """
    if theme.animation.rings_count <= 0:
        return

    p = theme.palette
    # Halka renkleri: dış-orta-iç → primary/secondary/primary
    palette_colors = [p.primary, p.secondary, p.primary]

    count = min(theme.animation.rings_count, len(_RING_SPECS))

    for idx in range(count):
        r_frac, pen_w, arc_len, gap = _RING_SPECS[idx]
        ring_r = face_width * r_frac
        base_angle = ring_angles[idx] if idx < len(ring_angles) else 0.0

        # Alpha: halo gücüne göre, dış halkadan içe doğru artar (idx=0 en parlak)
        a_val = max(0, min(255, int(halo_strength * (1.0 - idx * 0.18))))
        col_hex = p.warning if muted else palette_colors[idx]
        col = QColor(col_hex); col.setAlpha(a_val)

        painter.setPen(QPen(col, pen_w))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Arc'ı seg-seg çiz — toplam 360'ı dolaşana kadar
        rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
        angle = base_angle
        end = base_angle + 360
        while angle < end:
            painter.drawArc(rect, int(angle * 16), int(arc_len * 16))
            angle += arc_len + gap


def draw_ticks(
    painter: QPainter,
    cx: float, cy: float,
    face_width: float,
    theme: Theme,
) -> None:
    """Halkalarda saat ibresi gibi kısa çizgiler — her 10 derecede bir."""
    import math
    p = theme.palette
    t_out = face_width * 0.497
    t_in_short = face_width * 0.474
    t_in_long  = face_width * 0.474 + 6
    c = QColor(p.secondary); c.setAlpha(150)
    painter.setPen(QPen(c, 1))
    for deg in range(0, 360, 10):
        rad = math.radians(deg)
        inn = t_in_short if deg % 30 == 0 else t_in_long
        x1 = cx + t_out * math.cos(rad)
        y1 = cy - t_out * math.sin(rad)
        x2 = cx + inn * math.cos(rad)
        y2 = cy - inn * math.sin(rad)
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))


def draw_corner_brackets(
    painter: QPainter,
    cx: float, cy: float,
    face_width: float,
    theme: Theme,
    bracket_length: int = 24,
) -> None:
    """Köşelerde L şeklinde brackets — HUD karakteri verir."""
    p = theme.palette
    c = QColor(p.secondary); c.setAlpha(220)
    painter.setPen(QPen(c, 2))
    half = face_width / 2
    hl, hr = cx - half, cx + half
    ht, hb = cy - half, cy + half
    bl = bracket_length
    for bx, by, dx, dy in [
        (hl, ht,  1,  1),
        (hr, ht, -1,  1),
        (hl, hb,  1, -1),
        (hr, hb, -1, -1),
    ]:
        painter.drawLine(int(bx), int(by), int(bx + dx * bl), int(by))
        painter.drawLine(int(bx), int(by), int(bx), int(by + dy * bl))
