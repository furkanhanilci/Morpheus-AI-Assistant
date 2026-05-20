"""
Glitch efekti.

Face overlay'inin random olarak yatay/dikey küçük offset alması.
State'i bir GlitchState dataclass'ında tutuyoruz:
  • active     — şu an glitch çalışıyor mu
  • ttl        — kalan frame sayısı
  • offset_x/y — anki offset

step() her frame'de çağrılır:
  • Eğer aktifse ttl-- yapar, ttl=0 olunca passive olur.
  • Aktif değilse, speaking durumuna göre bir trigger olasılığı vardır.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class GlitchState:
    active: bool = False
    ttl: int = 0
    offset_x: float = 0.0
    offset_y: float = 0.0


def step(g: GlitchState, speaking: bool, enabled: bool) -> None:
    """Tek frame ilerlet."""
    if not enabled:
        g.active = False
        g.ttl = 0
        g.offset_x = 0.0
        g.offset_y = 0.0
        return

    if g.active:
        g.ttl -= 1
        if g.ttl <= 0:
            g.active = False
            g.offset_x = 0.0
            g.offset_y = 0.0
        return

    trigger_chance = 0.06 if speaking else 0.012
    if random.random() < trigger_chance:
        g.active = True
        g.ttl = random.randint(2, 5)
        g.offset_x = random.uniform(-6, 6)
        g.offset_y = random.uniform(-3, 3)
