"""
Halo glow + pulse rings.

İki katmanlı parçası var:
  • Halo glow      — face etrafında 10 katmanlı yumuşak yeşil glow
  • Pulse rings    — periyodik genişleyen halkalar (speaking sırasında hızlı)

Tema'nın `animation.halo_intensity` parametresi tüm yoğunluğu çarpan olarak ölçekler.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from ..themes import Theme


def draw_halo(
    painter: QPainter,
    cx: float, cy: float,
    face_radius: float,
    halo_strength: float,   # 0..200, animate edilen
    theme: Theme,
    muted: bool = False,
) -> None:
    """10 katmanlı concentric halo ring — face etrafında glow."""
    p = theme.palette
    base_color = p.warning if muted else p.primary
    intensity_mult = theme.animation.halo_intensity

    for i in range(10):
        r = face_radius * (1.8 - i * 0.08)
        frac = 1.0 - i / 10
        a = max(0, min(255, int(halo_strength * 0.085 * frac * intensity_mult)))
        c = QColor(base_color); c.setAlpha(a)
        painter.setPen(QPen(c, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))


def draw_pulses(
    painter: QPainter,
    cx: float, cy: float,
    pulses: list[float],     # radius listesi
    fade_distance: float,    # bu mesafeye kadar fade olur
    theme: Theme,
    muted: bool = False,
) -> None:
    """Genişleyen pulse halkaları çiz."""
    p = theme.palette
    base_color = p.warning if muted else p.primary

    for pr in pulses:
        a = max(0, int(220 * (1.0 - pr / fade_distance) * theme.animation.halo_intensity))
        if a <= 0:
            continue
        c = QColor(base_color); c.setAlpha(a)
        painter.setPen(QPen(c, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(cx - pr, cy - pr, pr * 2, pr * 2))


def draw_crosshair(
    painter: QPainter,
    cx: float, cy: float,
    outer_radius: float,
    gap: float,
    halo_strength: float,
    theme: Theme,
) -> None:
    """Crosshair (artı işareti) — face'in ortasında küçük boşluk bırakarak."""
    p = theme.palette
    a = int(halo_strength * 0.5 * theme.animation.halo_intensity)
    a = max(0, min(255, a))
    c = QColor(p.primary); c.setAlpha(a)
    painter.setPen(QPen(c, 1))
    painter.drawLine(int(cx - outer_radius), int(cy), int(cx - gap), int(cy))
    painter.drawLine(int(cx + gap), int(cy), int(cx + outer_radius), int(cy))
    painter.drawLine(int(cx), int(cy - outer_radius), int(cx), int(cy - gap))
    painter.drawLine(int(cx), int(cy + gap), int(cx), int(cy + outer_radius))
