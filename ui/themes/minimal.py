"""
Minimal teması.

Sade, dekoratif şeyler kapalı. Linear/Notion benzeri estetik.
Felsefe:
  • Grafit tonları, az kontrast
  • Subtle accent (yumuşak mavi)
  • Hiçbir Matrix/CRT etkisi yok
  • Halo çok zayıf, 1 tek halka, sadece breathing

Karanlık modda çalışan minimal palette — light mode opsiyonu PR-8'de eklenebilir.
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

_MONO_FAMILY    = "JetBrains Mono" if _OS == "Linux" else ("Consolas" if _OS == "Windows" else "SF Mono")
_MONO_FALLBACK  = "Menlo"
_SANS_FAMILY    = "Inter" if _OS == "Linux" else ("Segoe UI" if _OS == "Windows" else "SF Pro")


_PALETTE = Palette(
    # Backgrounds — yumuşak grafit katmanlar
    bg       = "#0e0f12",
    panel    = "#161820",
    panel_2  = "#1c1f28",
    dark     = "#0a0b0e",

    # Borders — soluk gri
    border        = "#2a2d36",
    border_dim    = "#1f2229",
    border_bright = "#404654",

    # Primary — yumuşak mavi (Linear vibe)
    primary       = "#8db4e2",
    primary_dim   = "#4f6a8a",
    primary_ghost = "#161e2a",

    # Secondary — açık gri (chrome)
    secondary       = "#a8afbd",
    secondary_dim   = "#5a6170",
    secondary_ghost = "#1a1d24",

    # Accent / warning / success
    accent   = "#e08070",
    warning  = "#e07560",
    success  = "#8dc890",

    # Text
    text         = "#d7dae0",
    text_dim     = "#6a7180",
    text_medium  = "#9aa1b0",
    text_strong  = "#f0f2f5",
)


_TYPOGRAPHY = Typography(
    mono_family   = _MONO_FAMILY,
    mono_fallback = _MONO_FALLBACK,
    sans_family   = _SANS_FAMILY,
)


_ANIMATION = AnimationParams(
    matrix_rain       = False,
    glitch            = False,
    particles         = False,
    scanlines         = False,
    halo_intensity    = 0.3,
    rings_count       = 1,
    waveform_bars     = 24,
    speak_pulse_speed = 0.7,
    idle_breathing    = True,
)


MINIMAL = Theme(
    name        = "Minimal",
    slug        = "minimal",
    description = "Quiet & focused. No decorations, just signal.",

    palette    = _PALETTE,
    typography = _TYPOGRAPHY,
    spacing    = Spacing(),
    animation  = _ANIMATION,

    # Sade İngilizce etiketler
    label_listening  = "Listening",
    label_speaking   = "Speaking",
    label_thinking   = "Thinking",
    label_processing = "Processing",
    label_jacking_in = "Connecting",
    label_muted      = "Muted",

    welcome_banner = "Claude · Minimal",
)
