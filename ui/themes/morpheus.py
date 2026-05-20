"""
Morpheus teması.

Mevcut ui.py'deki renk paletinin birebir port'u — visual continuity için.
Felsefe (yorum olarak da burada kalsın):
  • GREEN = canlı şeyler (Matrix rain, halo, "online" göstergeleri)
  • BLUE/NAVY = ölü chrome (panel zeminleri, border, button, sistem metni)
  • RED = uyarı / muted / red-pill aksanı
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

# OS bazlı font seçimi — Windows'ta Consolas, diğerlerinde Courier New
_MONO_FAMILY    = "Consolas" if _OS == "Windows" else "Courier New"
_MONO_FALLBACK  = "Courier New"
_SANS_FAMILY    = "Segoe UI" if _OS == "Windows" else "Helvetica"


_PALETTE = Palette(
    # Backgrounds — derin navy
    bg       = "#020610",
    panel    = "#06101e",
    panel_2  = "#0a1830",
    dark     = "#040912",

    # Borders — soğuk maviler
    border        = "#13294a",
    border_dim    = "#0e1f3a",
    border_bright = "#2960a0",

    # Primary — Matrix yeşili (kahraman renk, idareli kullan)
    primary       = "#00ff41",
    primary_dim   = "#1a8a3a",
    primary_ghost = "#062014",

    # Secondary — mavi ailesi (chrome)
    secondary       = "#4ea8ff",
    secondary_dim   = "#2a6db0",
    secondary_ghost = "#0a1a30",

    # Accent / warning / success
    accent   = "#ff5577",
    warning  = "#ff3a55",
    success  = "#00ff41",

    # Text
    text         = "#c4d8f5",
    text_dim     = "#5874a8",
    text_medium  = "#8aa3c9",
    text_strong  = "#e8f0ff",
)


_TYPOGRAPHY = Typography(
    mono_family   = _MONO_FAMILY,
    mono_fallback = _MONO_FALLBACK,
    sans_family   = _SANS_FAMILY,
)


_ANIMATION = AnimationParams(
    matrix_rain       = True,
    glitch            = True,
    particles         = True,
    scanlines         = True,
    halo_intensity    = 1.0,
    rings_count       = 3,
    waveform_bars     = 36,
    speak_pulse_speed = 1.0,
    idle_breathing    = True,
)


MORPHEUS = Theme(
    name        = "Morpheus",
    slug        = "morpheus",
    description = "Matrix construct. Maximum atmosphere — rain, glitch, halo.",

    palette    = _PALETTE,
    typography = _TYPOGRAPHY,
    spacing    = Spacing(),     # default token'lar
    animation  = _ANIMATION,

    # Peaky-flavored Matrix sözlüğü
    label_listening  = "AWAITING INPUT",
    label_speaking   = "TRANSMITTING",
    label_thinking   = "DECODING",
    label_processing = "COMPILING",
    label_jacking_in = "JACKING IN",
    label_muted      = "SIGNAL BLOCKED",

    welcome_banner = "MORPHEUS — Construct v9",
)
