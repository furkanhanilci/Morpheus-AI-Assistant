"""
Theme base — şema.

Her tema (Morpheus, Mission Control, Minimal) bu dataclass'ı doldurur.
UI component'ları renk/font/spacing'i HER ZAMAN aktif tema üzerinden okur,
asla hardcoded değer kullanmaz.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PerfLevel(Enum):
    """Animasyon yoğunluğu — performance mode için."""
    OFF    = 0   # animasyon yok, sadece state geçişleri
    LOW    = 1   # 20 fps, decorative animasyonlar kapalı
    NORMAL = 2   # 30 fps, çoğu animasyon açık
    HIGH   = 3   # 60 fps, hepsi açık (matrix rain, glitch, particles)


@dataclass(frozen=True)
class Palette:
    """Renk paleti. Hex string (#rrggbb) formatında."""
    # Backgrounds — katmanlı arka planlar
    bg:       str           # ana arka plan (window)
    panel:    str           # 1. katman panel
    panel_2:  str           # 2. katman panel (daha açık veya koyu)
    dark:     str           # header/footer için en koyu ton

    # Borders
    border:        str
    border_dim:    str      # daha soluk border
    border_bright: str      # vurgulu border (hover, focus)

    # Primary — temanın hero rengi
    primary:        str
    primary_dim:    str
    primary_ghost:  str     # düşük opaklıkta zemin

    # Secondary — chrome rengi (genelde mavi/gri)
    secondary:        str
    secondary_dim:    str
    secondary_ghost:  str

    # Accent — uyarı/aksiyon
    accent:   str           # genelde kırmızı/turuncu
    warning:  str
    success:  str

    # Text
    text:        str        # ana okunur metin
    text_dim:    str        # ikincil metin
    text_medium: str        # arada bir ton
    text_strong: str        # vurgu (başlık, sayı)


@dataclass(frozen=True)
class Typography:
    """Font tanımları."""
    mono_family:    str     # ana monospace font (kod, log, HUD)
    mono_fallback:  str     # OS yoksa fallback
    sans_family:    str     # ikincil (başlık, modal)

    size_xs:    int = 7
    size_sm:    int = 8
    size_base:  int = 9
    size_md:    int = 10
    size_lg:    int = 12
    size_xl:    int = 14
    size_2xl:   int = 18


@dataclass(frozen=True)
class Spacing:
    """Padding/margin token'ları. Magic number yok."""
    xs:  int = 2
    sm:  int = 4
    md:  int = 6
    lg:  int = 8
    xl:  int = 12
    xxl: int = 18

    radius_sm: int = 3
    radius_md: int = 4
    radius_lg: int = 6

    border_w:    int = 1
    border_w_em: int = 2   # vurgulu

    # Layout sabitleri
    sidebar_w:   int = 160
    right_dock_w: int = 360
    header_h:    int = 36
    footer_h:    int = 22


@dataclass(frozen=True)
class AnimationParams:
    """Tema-bazlı animasyon karakteri."""
    matrix_rain:        bool  = False  # Matrix yağmuru çizilsin mi
    glitch:             bool  = False  # glitch efekti
    particles:          bool  = False  # parçacık efekti (speaking)
    scanlines:          bool  = False  # CRT scanline efekti

    halo_intensity:     float = 1.0    # 0..2, halo glow yoğunluğu
    rings_count:        int   = 3      # spinning ring sayısı (0–3)
    waveform_bars:      int   = 36     # input waveform bar sayısı

    speak_pulse_speed:  float = 1.0    # speaking sırasında nabız hızı çarpanı
    idle_breathing:     bool  = True   # idle durumunda nefes alan animasyon


@dataclass(frozen=True)
class Theme:
    """
    Bir UI temasının tüm görsel + davranışsal parametrelerini taşır.

    Tema değiştirmek = bu objeyi swap etmek + signal_bus.theme_changed emit etmek.
    Hiçbir component bu objenin attribute'ları dışında dış bilgi kullanmaz.
    """
    name:        str          # "Morpheus", "Mission Control", "Minimal"
    slug:        str          # "morpheus", "mission_control", "minimal"
    description: str          # tooltip / settings için kısa açıklama

    palette:     Palette
    typography:  Typography
    spacing:     Spacing      = field(default_factory=Spacing)
    animation:   AnimationParams = field(default_factory=AnimationParams)

    # Tema-özel string'ler (UI string'lerini tema karakterine uydurmak için)
    # Örn. Morpheus için "JACKING IN", Minimal için "Connecting...", MC için "INITIALIZING"
    label_listening:  str = "LISTENING"
    label_speaking:   str = "SPEAKING"
    label_thinking:   str = "THINKING"
    label_jacking_in: str = "CONNECTING"
    label_muted:      str = "MUTED"
    label_processing: str = "PROCESSING"

    # Welcome banner — header'da gösterilebilir
    welcome_banner: str = ""
