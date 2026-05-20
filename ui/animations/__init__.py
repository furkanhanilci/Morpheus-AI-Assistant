"""
ui.animations — paint primitive'leri.

Her modül stateless çizim fonksiyonları sağlar (state'i çağıran tutar).
Tema'nın `animation` AnimationParams'ına göre HudCanvas hangi modülün
draw fonksiyonunu çağıracağına karar verir.
"""
from . import face, glitch, halo, matrix_rain, particles, rings, scanlines, scanner, waveform

__all__ = [
    "face", "glitch", "halo", "matrix_rain", "particles",
    "rings", "scanlines", "scanner", "waveform",
]
