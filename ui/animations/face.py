"""
Face overlay — yüklenen PNG'yi face area'nın merkezine çizer.

PNG yoksa "MORPHEUS" yazılı bir orb fallback'i kullanır.
Glitch aktif iken hafif şeffaf bir kopyasını offset'le birlikte çizer (chromatic-shift hissi).
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPen, QPixmap,
)

from ..themes import Theme
from .glitch import GlitchState


def load_face_pixmap(path: str) -> Optional[QPixmap]:
    """PNG'yi yuvarlak alpha mask ile yükler. Yoksa None döner."""
    try:
        from PIL import Image, ImageDraw
        if not path or not Path(path).exists():
            return None
        img = Image.open(path).convert("RGBA")
        sz = min(img.size)
        img = img.resize((sz, sz), Image.LANCZOS)
        mk = Image.new("L", (sz, sz), 0)
        ImageDraw.Draw(mk).ellipse((2, 2, sz - 2, sz - 2), fill=255)
        img.putalpha(mk)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        px = QPixmap()
        px.loadFromData(buf.getvalue())
        return px
    except Exception:
        return None


def draw(
    painter: QPainter,
    cx: float, cy: float,
    face_width: float,
    scale: float,            # animate edilen "nefes" çarpanı
    halo_strength: float,    # fallback orb için
    face_pixmap: Optional[QPixmap],
    glitch: GlitchState,
    theme: Theme,
    muted: bool = False,
) -> None:
    """Yüzü merkez bölgeye çiz."""
    p = theme.palette
    gx = glitch.offset_x if glitch.active else 0.0
    gy = glitch.offset_y if glitch.active else 0.0

    if face_pixmap is not None:
        fsz = int(face_width * 0.62 * scale)
        scaled = face_pixmap.scaled(
            fsz, fsz,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if glitch.active:
            # Şeffaf ghost copy
            painter.setOpacity(0.4)
            painter.drawPixmap(
                int(cx - fsz / 2 - gx * 1.5),
                int(cy - fsz / 2),
                scaled,
            )
            painter.setOpacity(1.0)
        painter.drawPixmap(
            int(cx - fsz / 2 + gx),
            int(cy - fsz / 2 + gy),
            scaled,
        )
    else:
        # Fallback orb — tema'nın primary tonunda
        orb_r = int(face_width * 0.27 * scale)
        if muted:
            oc_hex = p.warning
        else:
            oc_hex = p.primary
        oc_col = QColor(oc_hex)
        oc_base = (oc_col.red(), oc_col.green(), oc_col.blue())
        # Çok parlak renkleri sönükleştir (orb gradient için)
        oc = (oc_base[0] // 3, oc_base[1] // 3, oc_base[2] // 3)

        for i in range(8, 0, -1):
            r2 = int(orb_r * i / 8)
            frc = i / 8
            a = max(0, min(255, int(halo_strength * 1.1 * frc)))
            painter.setBrush(QBrush(QColor(
                int(oc[0] * frc * 1.5), int(oc[1] * frc * 1.5), int(oc[2] * frc * 1.5), a
            )))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2))

        # Label — tema adı, uzunsa font küçülür ve genişlik artar
        c = QColor(p.primary); c.setAlpha(min(255, int(halo_strength * 2)))
        painter.setPen(QPen(c, 1))
        label = theme.name.upper()
        # 8 karakterden uzunsa font'u küçült
        font_size = 16 if len(label) <= 8 else (13 if len(label) <= 14 else 11)
        painter.setFont(QFont(theme.typography.mono_family, font_size, QFont.Weight.Bold))
        text_w = max(200, len(label) * font_size)
        painter.drawText(
            QRectF(cx - text_w / 2, cy - 14, text_w, 28),
            Qt.AlignmentFlag.AlignCenter,
            label,
        )
