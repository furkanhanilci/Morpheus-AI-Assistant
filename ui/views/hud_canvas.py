"""
HudCanvas — animasyonların kompozit edildiği merkezî widget.

Çalışma prensibi:
  1. QTimer her frame'de _step() çağırır
     • Animasyon state'lerini (halo, scale, rings, particles, glitch, rain) ilerletir
     • Frame interval Performance Mode'a göre değişir
  2. paintEvent() aktif temanın AnimationParams'ına bakar
     • İlgili animation modülünün draw() fonksiyonunu çağırır
     • Kapalı animasyonlar hiç çizilmez (no-op)

State'i bu sınıf tutar; animation modülleri sadece çizici (stateless'a yakın).
"""
from __future__ import annotations

import math
import random
import time
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..animations import face, glitch, halo, matrix_rain, particles, rings, scanlines, scanner, waveform
from ..animations.glitch import GlitchState
from ..animations.matrix_rain import RainField
from ..state import bus, state, ConnState
from ..themes import PerfLevel, Theme, get_theme


# Frame interval (ms) per PerfLevel
_FRAME_INTERVAL = {
    PerfLevel.OFF:    0,      # timer dur
    PerfLevel.LOW:    50,     # 20 fps
    PerfLevel.NORMAL: 33,     # 30 fps
    PerfLevel.HIGH:   16,     # 60 fps
}


class HudCanvas(QWidget):
    """
    Tema-aware animasyon compositor.

    Public:
      • set_face(path)        — face PNG yolu (constructor'da set edilebilir)
      • muted / speaking      — property setter'lar (HUD'a state aktarımı)

    State machine'i UIState üzerinden okur (bus.state_changed ve
    bus.speaking_set sinyallerini dinler).
    """

    def __init__(self, face_path: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # ─── Local mirrors of state ───────────────────────────────────────────
        self._muted    = state.muted
        self._speaking = state.speaking
        self._state    = state.conn_state.value
        self._ptt_active = state.ptt_active

        # ─── Animation state ──────────────────────────────────────────────────
        self._tick       = 0
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._halo       = 55.0
        self._tgt_halo   = 55.0
        self._last_t     = time.time()

        # Rings — başlangıç açıları
        self._ring_angles: list[float] = [0.0, 120.0, 240.0]
        # Scanner — primary ve secondary açılar
        self._scan_p = 0.0
        self._scan_s = 180.0
        # Pulses — radius listesi
        self._pulses: list[float] = [0.0, 50.0, 100.0]
        # Particles
        self._particles: list[list] = []
        # Glitch state
        self._glitch = GlitchState()
        # Matrix rain field
        self._rain = RainField()
        # Status blink
        self._blink = True
        self._blink_tick = 0

        # ─── Face ─────────────────────────────────────────────────────────────
        self._face_pixmap = face.load_face_pixmap(face_path) if face_path else None

        # ─── Timer ────────────────────────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._apply_perf_level(state.perf_level)

        # ─── Bus listeners ────────────────────────────────────────────────────
        bus.state_changed.connect(self._on_state_changed)
        bus.speaking_set.connect(self._on_speaking_set)
        bus.mute_set.connect(self._on_mute_set)
        bus.theme_changed.connect(self._on_theme_changed)
        bus.perf_mode_changed.connect(self._on_perf_changed)
        bus.ptt_pressed.connect(self._on_ptt_pressed)
        bus.ptt_released.connect(self._on_ptt_released)

    # ─── Public API ───────────────────────────────────────────────────────────
    def set_face(self, path: str) -> None:
        self._face_pixmap = face.load_face_pixmap(path)
        self.update()

    # ─── Signal handlers ──────────────────────────────────────────────────────
    def _on_state_changed(self, value: str) -> None:
        self._state = value
        self.update()

    def _on_speaking_set(self, value: bool) -> None:
        self._speaking = value

    def _on_mute_set(self, value: bool) -> None:
        self._muted = value
        self.update()

    def _on_ptt_pressed(self) -> None:
        self._ptt_active = True
        self.update()

    def _on_ptt_released(self) -> None:
        self._ptt_active = False
        self.update()

    def _on_theme_changed(self, _theme: Theme) -> None:
        # Yeni temanın AnimationParams'ı farklı olabilir → sadece tekrar boya
        self.update()

    def _on_perf_changed(self, level_value: int) -> None:
        try:
            level = PerfLevel(level_value)
        except ValueError:
            return
        self._apply_perf_level(level)

    def _apply_perf_level(self, level: PerfLevel) -> None:
        if level == PerfLevel.OFF:
            self._timer.stop()
            self.update()
            return
        interval = _FRAME_INTERVAL.get(level, 16)
        self._timer.start(interval)

    # ─── Resize ───────────────────────────────────────────────────────────────
    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        self._rain.ensure_size(self.width(), self.height())

    # ─── Step (state update) ──────────────────────────────────────────────────
    def _step(self) -> None:
        self._tick += 1
        now = time.time()

        # Rain init/resize
        self._rain.ensure_size(self.width(), self.height())

        th = get_theme()
        anim = th.animation
        speaking = self._speaking
        muted    = self._muted

        # Halo + scale targets (breathing)
        change_interval = 0.12 if speaking else 0.5
        if now - self._last_t > change_interval:
            if speaking:
                self._tgt_scale = random.uniform(1.06, 1.14)
                self._tgt_halo  = random.uniform(145, 190)
            elif muted:
                self._tgt_scale = random.uniform(0.998, 1.002)
                self._tgt_halo  = random.uniform(15, 28)
            elif anim.idle_breathing:
                self._tgt_scale = random.uniform(1.001, 1.008)
                self._tgt_halo  = random.uniform(48, 68)
            else:
                self._tgt_scale = 1.0
                self._tgt_halo  = 45
            self._last_t = now

        smooth = 0.38 if speaking else 0.15
        self._scale += (self._tgt_scale - self._scale) * smooth
        self._halo  += (self._tgt_halo  - self._halo)  * smooth

        # Rings dönüş
        ring_speeds = [1.3, -0.9, 2.0] if speaking else [0.55, -0.35, 0.9]
        for i, spd in enumerate(ring_speeds):
            if i < len(self._ring_angles):
                self._ring_angles[i] = (self._ring_angles[i] + spd) % 360

        # Scanner dönüş
        self._scan_p = (self._scan_p + (3.0  if speaking else  1.3)) % 360
        self._scan_s = (self._scan_s + (-2.0 if speaking else -0.75)) % 360

        # Pulses
        fw = min(self.width(), self.height())
        fade_dist = fw * 0.74
        pulse_speed = 4.2 if speaking else 2.0
        self._pulses = [r + pulse_speed for r in self._pulses if r + pulse_speed < fade_dist]
        spawn_chance = 0.07 if speaking else 0.025
        if len(self._pulses) < 3 and random.random() < spawn_chance:
            self._pulses.append(0.0)

        # Particles (tema + speaking + perf)
        if anim.particles and speaking and state.perf_level.value >= PerfLevel.NORMAL.value:
            cx, cy = self.width() / 2, self.height() / 2
            particles.spawn(self._particles, cx, cy, fw, spawn_chance=0.28)
        self._particles = particles.step(self._particles)

        # Matrix rain — perf NORMAL+ ve tema açıksa
        if anim.matrix_rain and state.perf_level.value >= PerfLevel.NORMAL.value:
            self._rain.step()

        # Glitch (tema + perf NORMAL+ ile aktif)
        glitch_enabled = anim.glitch and state.perf_level.value >= PerfLevel.NORMAL.value
        glitch.step(self._glitch, speaking, glitch_enabled)

        # Status text blink
        self._blink_tick += 1
        if self._blink_tick >= 38:
            self._blink = not self._blink
            self._blink_tick = 0

        self.update()

    # ─── Paint (compositor) ───────────────────────────────────────────────────
    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        th = get_theme()
        anim = th.animation
        palette_obj = th.palette

        # Background
        p.fillRect(self.rect(), QColor(palette_obj.bg))

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        fw = min(W, H)

        # 1. Matrix rain (tema)
        if anim.matrix_rain:
            matrix_rain.draw(p, self._rain, th)

        # 2. Scanlines (tema)
        if anim.scanlines:
            scanlines.draw(p, self.rect(), th)

        r_face = fw * 0.31

        # 3. Halo (her tema kullanır)
        halo.draw_halo(p, cx, cy, r_face, self._halo, th, muted=self._muted)

        # 4. Pulses
        halo.draw_pulses(p, cx, cy, self._pulses, fw * 0.74, th, muted=self._muted)

        # 5. Rings (tema'nın sayısı kadar)
        rings.draw(p, cx, cy, fw, self._ring_angles, self._halo, th, muted=self._muted)

        # 6. Scanner arcs
        scanner.draw(p, cx, cy, fw, self._scan_p, self._scan_s, self._halo, th,
                     speaking=self._speaking, muted=self._muted)

        # 7. Tick marks (her tema bunu kullanır)
        rings.draw_ticks(p, cx, cy, fw, th)

        # 8. Crosshair (face etrafında küçük artı)
        halo.draw_crosshair(p, cx, cy, fw * 0.51, fw * 0.16, self._halo, th)

        # 9. Corner brackets
        rings.draw_corner_brackets(p, cx, cy, fw, th, bracket_length=24)

        # 10. Face overlay
        face.draw(p, cx, cy, fw, self._scale, self._halo,
                  self._face_pixmap, self._glitch, th, muted=self._muted)

        # 11. Particles (tema açıksa ve perf izin verirse — step zaten kontrol etti)
        if anim.particles and self._particles:
            particles.draw(p, self._particles, th)

        # 12. Status text
        self._draw_status_text(p, cx, cy, fw, th)

        # 13. Waveform (alt)
        waveform.draw(p, cx, cy, fw, self._tick, th,
                      speaking=self._speaking, muted=self._muted)

        # 14. PTT badge — sağ üst köşede, sadece PTT modu aktif ve basılıyken
        if self._ptt_active:
            self._draw_ptt_badge(p, th)

    # ─── Status text ──────────────────────────────────────────────────────────
    def _draw_status_text(self, p: QPainter, cx: float, cy: float,
                          fw: float, theme: Theme) -> None:
        """HUD'un altında durum etiketi: '● TRANSMITTING' vs."""
        sy = cy + fw * 0.40

        if self._muted:
            txt = f"⊘  {theme.label_muted}"
            col_hex = theme.palette.warning
        elif self._speaking:
            txt = f"●  {theme.label_speaking}"
            col_hex = theme.palette.primary
        elif self._state == ConnState.THINKING.value:
            sym = "◈" if self._blink else "◇"
            txt = f"{sym}  {theme.label_thinking}"
            col_hex = theme.palette.secondary
        elif self._state == ConnState.PROCESSING.value:
            sym = "▷" if self._blink else "▶"
            txt = f"{sym}  {theme.label_processing}"
            col_hex = theme.palette.secondary
        elif self._state == ConnState.LISTENING.value:
            sym = "●" if self._blink else "○"
            txt = f"{sym}  {theme.label_listening}"
            col_hex = theme.palette.success
        elif self._state == ConnState.JACKING_IN.value:
            sym = "●" if self._blink else "○"
            txt = f"{sym}  {theme.label_jacking_in}"
            col_hex = theme.palette.secondary
        else:
            txt = f"●  {self._state}"
            col_hex = theme.palette.primary

        c = QColor(col_hex)
        p.setPen(QPen(c, 1))
        p.setFont(QFont(theme.typography.mono_family, 11, QFont.Weight.Bold))
        W = self.width()
        p.drawText(
            QRectF(0, sy, W, 26),
            Qt.AlignmentFlag.AlignCenter,
            txt,
        )

    def _draw_ptt_badge(self, painter: QPainter, theme: Theme) -> None:
        """PTT aktif iken sağ üst köşede '🎙 PTT' rozeti."""
        from PyQt6.QtGui import QBrush
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        W = self.width()
        badge_w = 90
        badge_h = 28
        x = W - badge_w - s.lg
        y = s.lg

        # Background pulsing — tick'e göre alfa
        pulse = abs((self._tick % 60) - 30) / 30  # 0..1
        bg_alpha = int(180 + 60 * pulse)
        bg_col = QColor(p.primary); bg_col.setAlpha(bg_alpha)

        painter.setBrush(QBrush(bg_col))
        painter.setPen(QPen(QColor(p.primary), 1))
        painter.drawRoundedRect(
            QRectF(x, y, badge_w, badge_h),
            s.radius_sm, s.radius_sm,
        )

        # Text
        painter.setPen(QPen(QColor(p.dark), 1))
        painter.setFont(QFont(t.mono_family, t.size_xs, QFont.Weight.Bold))
        painter.drawText(
            QRectF(x, y, badge_w, badge_h),
            Qt.AlignmentFlag.AlignCenter,
            "🎙  PTT LIVE",
        )


__all__ = ["HudCanvas"]
