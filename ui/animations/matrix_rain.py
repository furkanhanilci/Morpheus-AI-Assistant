"""
Matrix digital rain.

Eski ui.py'deki _RainColumn + draw kodunun bir araya getirilmiş hali.
Tema-aware: rain renkleri palette.primary'den okur.

Kullanım:
    field = RainField(width, height)
    field.step()
    rain_field.draw(painter, field, theme)
"""
from __future__ import annotations

import random

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen

from ..themes import Theme


_MATRIX_CHARS = (
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ":・.\"=*+-<>¦|çﾘｸ"
)


class RainColumn:
    """Tek bir yağmur sütunu — x sabit, y aşağı doğru iner."""
    __slots__ = ("x", "y", "speed", "length", "chars", "head_glow")

    def __init__(self, x: float, height: int):
        self.x = x
        self.y = random.uniform(-height, 0)
        self.speed = random.uniform(2.0, 5.5)
        self.length = random.randint(8, 22)
        self.chars = [random.choice(_MATRIX_CHARS) for _ in range(self.length)]
        self.head_glow = random.random() < 0.4

    def step(self, height: int, char_h: int) -> None:
        self.y += self.speed
        # %18 ihtimalle bir karakter değiştir — "live" his
        if random.random() < 0.18:
            i = random.randint(0, self.length - 1)
            self.chars[i] = random.choice(_MATRIX_CHARS)
        # Sütun ekranın altına geçtiyse üstten yeniden başla
        if self.y - self.length * char_h > height:
            self.y = random.uniform(-height * 0.5, -char_h)
            self.speed = random.uniform(2.0, 5.5)
            self.length = random.randint(8, 22)
            self.chars = [random.choice(_MATRIX_CHARS) for _ in range(self.length)]
            self.head_glow = random.random() < 0.4


class RainField:
    """Sütun koleksiyonu + step + resize."""

    def __init__(self, char_w: int = 12, char_h: int = 16):
        self.char_w = char_w
        self.char_h = char_h
        self._cols: list[RainColumn] = []
        self._w = 0
        self._h = 0
        self._inited = False

    def ensure_size(self, width: int, height: int) -> None:
        """Pencere boyutu değiştiyse sütun setini yeniden oluştur."""
        if width < 10 or height < 10:
            return
        if self._inited and width == self._w and height == self._h:
            return
        self._w = width
        self._h = height
        cols = max(8, width // self.char_w)
        self._cols = [
            RainColumn(i * self.char_w + random.uniform(-3, 3), height)
            for i in range(cols)
        ]
        self._inited = True

    def step(self) -> None:
        if not self._inited:
            return
        for col in self._cols:
            col.step(self._h, self.char_h)

    def columns(self) -> list[RainColumn]:
        return self._cols


def draw(painter: QPainter, field: RainField, theme: Theme,
         font_family: str = "") -> None:
    """RainField'ı verilen painter üzerine çiz."""
    if not field._inited:
        return
    p = theme.palette
    t = theme.typography
    font = QFont(font_family or t.mono_family, 10)
    font.setBold(True)
    painter.setFont(font)

    primary_col = p.primary
    head_col    = "#d8ffd8"  # baş karakteri için açık yeşil, palette'te yok bu yüzden sabit

    for col in field.columns():
        for i, ch in enumerate(col.chars):
            yy = col.y - i * field.char_h
            if yy < -field.char_h or yy > field._h + field.char_h:
                continue
            if i == 0:
                a = 220 if col.head_glow else 190
                c = QColor(head_col); c.setAlpha(a)
                painter.setPen(QPen(c, 1))
            else:
                frac = 1.0 - (i / col.length)
                a = int(150 * frac * frac)
                if a < 6:
                    continue
                c = QColor(primary_col); c.setAlpha(a)
                painter.setPen(QPen(c, 1))
            painter.drawText(QPointF(col.x, yy), ch)
