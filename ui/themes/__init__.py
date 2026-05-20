"""
Theme Manager.

Public API:
    from ui.themes import get_theme, switch_theme, available_themes

    theme = get_theme()           # aktif Theme objesi
    switch_theme("minimal")       # tema değiştir, signal emit eder

Tema değişikliği SignalBus.theme_changed üzerinden tüm component'lara yayılır.
Component'lar bu signal'ı dinleyip kendi paint/style'ını yeniler.
"""
from __future__ import annotations

import threading
from typing import Callable

from .base import Theme, PerfLevel, Palette, Typography, Spacing, AnimationParams
from .morpheus import MORPHEUS
from .mission_control import MISSION_CONTROL
from .minimal import MINIMAL

# PR-5: üç tema artık aktif.
# Sıra UI'da gösterim sırasıdır.
_REGISTRY: dict[str, Theme] = {
    MORPHEUS.slug:        MORPHEUS,
    MISSION_CONTROL.slug: MISSION_CONTROL,
    MINIMAL.slug:         MINIMAL,
}

# Default tema = Morpheus
_active_slug: str = MORPHEUS.slug

# Theme-change listener'ları. SignalBus henüz import edilmeden de çalışsın diye
# basit bir callback listesi tutuyoruz; SignalBus PR-1 sonunda bağlanır.
_listeners: list[Callable[[Theme], None]] = []
_lock = threading.Lock()


def register_theme(theme: Theme) -> None:
    """Yeni bir tema register et. Slug çakışırsa override eder."""
    with _lock:
        _REGISTRY[theme.slug] = theme


def available_themes() -> list[Theme]:
    """Kayıtlı tüm temalar."""
    return list(_REGISTRY.values())


def get_theme(slug: str | None = None) -> Theme:
    """
    Tema getir. slug verilmezse aktif tema dönülür.
    Bilinmeyen slug → aktif tema (sessiz fallback).
    """
    if slug is None:
        slug = _active_slug
    return _REGISTRY.get(slug, _REGISTRY[_active_slug])


def active_slug() -> str:
    return _active_slug


def switch_theme(slug: str) -> Theme:
    """
    Aktif temayı değiştir. Tüm listener'lara yeni temayı yayar.
    Geçersiz slug → no-op, mevcut tema döner.
    """
    global _active_slug

    with _lock:
        if slug not in _REGISTRY:
            return _REGISTRY[_active_slug]
        if slug == _active_slug:
            return _REGISTRY[_active_slug]
        _active_slug = slug
        new_theme = _REGISTRY[slug]
        listeners_snapshot = list(_listeners)

    # listener'ları lock dışında çağır — deadlock'tan kaçınmak için
    for cb in listeners_snapshot:
        try:
            cb(new_theme)
        except Exception as e:
            print(f"[ThemeManager] listener error: {e}")

    return new_theme


def add_listener(callback: Callable[[Theme], None]) -> None:
    """Tema değiştiğinde çağrılacak callback ekle."""
    with _lock:
        if callback not in _listeners:
            _listeners.append(callback)


def remove_listener(callback: Callable[[Theme], None]) -> None:
    with _lock:
        if callback in _listeners:
            _listeners.remove(callback)


__all__ = [
    "Theme", "PerfLevel", "Palette", "Typography", "Spacing", "AnimationParams",
    "get_theme", "switch_theme", "active_slug",
    "available_themes", "register_theme",
    "add_listener", "remove_listener",
    "MORPHEUS", "MISSION_CONTROL", "MINIMAL",
]
