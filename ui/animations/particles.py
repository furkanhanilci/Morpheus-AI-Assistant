"""
Particle field — speaking sırasında face etrafından yayılan parçacıklar.

Her parçacık: [x, y, vx, vy, life].  Life 1.0 → 0.0'a düşer, sonra silinir.
"""
from __future__ import annotations

import math
import random

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter

from ..themes import Theme


Particle = list  # [x, y, vx, vy, life]


def spawn(
    particles: list[Particle],
    cx: float, cy: float,
    face_width: float,
    spawn_chance: float = 0.28,
) -> None:
    """Tek bir frame'de bir parçacık spawn etme şansı."""
    if random.random() >= spawn_chance:
        return
    ang = random.uniform(0, 2 * math.pi)
    r_s = face_width * 0.28
    particles.append([
        cx + math.cos(ang) * r_s,
        cy + math.sin(ang) * r_s,
        math.cos(ang) * random.uniform(0.9, 2.4),
        math.sin(ang) * random.uniform(0.9, 2.4) - 0.4,
        1.0,
    ])


def step(particles: list[Particle]) -> list[Particle]:
    """Her parçacığı bir adım ilerlet, ölü olanları sil."""
    return [
        [pt[0] + pt[2], pt[1] + pt[3], pt[2] * 0.97, pt[3] * 0.97, pt[4] - 0.028]
        for pt in particles
        if pt[4] > 0
    ]


def draw(
    painter: QPainter,
    particles: list[Particle],
    theme: Theme,
) -> None:
    p = theme.palette
    painter.setPen(Qt.PenStyle.NoPen)
    for pt in particles:
        a = max(0, min(255, int(pt[4] * 255)))
        c = QColor(p.primary); c.setAlpha(a)
        painter.setBrush(QBrush(c))
        painter.drawEllipse(QPointF(pt[0], pt[1]), 2.5, 2.5)
