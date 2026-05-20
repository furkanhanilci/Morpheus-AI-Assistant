"""
Mission Control teması.

NASA/JPL kontrol odası estetiği. Karsan AV stack'in hissi.
Felsefe:
  • AMBER  = aktif/canlı işaretler (status, speaking, telemetry)
  • PETROL BLUE = chrome (border, panel zemini, sistem metni)
  • RED    = warning/abort/muted
  • DEEP NAVY = arka plan katmanları

Matrix rain ve glitch yok — bunlar Morpheus'a özel atmosfer.
Particles + scanlines var — kontrol ekranı hissi.
"""
from __future__ import annotations

import platform

from .base import (
    AnimationParams,
    Palette,
    Spacing,
    Theme,
    Typography,
)

_OS = platform.system()

_MONO_FAMILY    = "Consolas" if _OS == "Windows" else "Courier New"
_MONO_FALLBACK  = "Courier New"
_SANS_FAMILY    = "Segoe UI" if _OS == "Windows" else "Helvetica"


_PALETTE = Palette(
    # Backgrounds — derin lacivert/petrol
    bg       = "#06121c",
    panel    = "#0c1e2c",
    panel_2  = "#13293c",
    dark     = "#040c14",

    # Borders — petrol mavi tonları
    border        = "#1f4358",
    border_dim    = "#163242",
    border_bright = "#4a8aa8",

    # Primary — AMBER (hero rengi, telemetry/status)
    primary       = "#ffb142",
    primary_dim   = "#b07020",
    primary_ghost = "#1f1a0d",

    # Secondary — petrol/cyan mavi (chrome)
    secondary       = "#5fb3d0",
    secondary_dim   = "#326b80",
    secondary_ghost = "#0c2530",

    # Accent / warning / success
    accent   = "#ff7b6a",      # turuncu-kırmızı (abort key)
    warning  = "#ff5b4a",
    success  = "#7adc7a",      # yumuşak yeşil (göstergeler için)

    # Text
    text         = "#cfe4f0",
    text_dim     = "#5d8298",
    text_medium  = "#8fb0c4",
    text_strong  = "#f0f8ff",
)


_TYPOGRAPHY = Typography(
    mono_family   = _MONO_FAMILY,
    mono_fallback = _MONO_FALLBACK,
    sans_family   = _SANS_FAMILY,
)


_ANIMATION = AnimationParams(
    matrix_rain       = False,  # Morpheus'a özel
    glitch            = False,  # NASA paneli titremez
    particles         = True,   # speaking sırasında telemetry partikülleri
    scanlines         = True,   # CRT monitor karakteri
    halo_intensity    = 0.75,
    rings_count       = 2,      # daha az, daha sakin
    waveform_bars     = 32,
    speak_pulse_speed = 0.85,
    idle_breathing    = True,
)


MISSION_CONTROL = Theme(
    name        = "Mission Control",
    slug        = "mission_control",
    description = "NASA/JPL operations console. Amber telemetry, calmer animations.",

    palette    = _PALETTE,
    typography = _TYPOGRAPHY,
    spacing    = Spacing(),
    animation  = _ANIMATION,

    # NASA tarzı operasyon sözlüğü
    label_listening  = "STANDBY",
    label_speaking   = "TRANSMITTING",
    label_thinking   = "PROCESSING",
    label_processing = "COMPUTING",
    label_jacking_in = "INITIALIZING",
    label_muted      = "COMM SILENT",

    welcome_banner = "MISSION CONTROL — Bursa",
)
