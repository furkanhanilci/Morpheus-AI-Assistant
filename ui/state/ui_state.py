"""
UIState — uygulamanın yaşayan durumu.

Bir tek instance'ı var (`state`), tüm UI bunu okur ve setter'lar üzerinden değiştirir.
Setter'lar SignalBus üzerinden ilgili event'i emit eder, böylece component'lar
ya state objesini polling'le değil, signal'la dinler.

Bu, mevcut ui.py'deki dağınık `self._muted`, `hud.muted`, `hud.speaking`,
`hud.state` gibi pek çok yere kopyalanan flag'leri tek yerde toplar.
"""
from __future__ import annotations

import threading
from enum import Enum
from typing import Optional

from ..themes import PerfLevel, Theme, get_theme, switch_theme
from .signals import bus


class ConnState(str, Enum):
    """Asistanın o anki anlamsal durumu."""
    JACKING_IN  = "JACKING IN"   # backend'e bağlanıyor (Gemini Live)
    LISTENING   = "LISTENING"    # mikrofon açık, kullanıcı konuşmasını bekliyor
    SPEAKING    = "SPEAKING"     # asistan ses çıkarıyor
    THINKING    = "THINKING"     # tool çağrıldı, sonuç bekleniyor
    PROCESSING  = "PROCESSING"   # uzun süren işlem (agent plan)
    MUTED       = "MUTED"        # kullanıcı mute etti


class ListeningMode(str, Enum):
    ALWAYS = "always"   # sürekli dinle (default)
    PTT    = "ptt"      # push-to-talk (SPACE)
    OFF    = "off"      # sadece text input


class UIState:
    """
    Thread-safe durum container.
    Setter'lar idempotent — aynı değeri tekrar set etmek signal emit etmez.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # State
        self._conn_state: ConnState = ConnState.JACKING_IN
        self._muted: bool           = False
        self._speaking: bool        = False

        # Theme / Performance
        self._perf_level: PerfLevel = PerfLevel.HIGH

        # Input
        self._listening_mode: ListeningMode = ListeningMode.ALWAYS
        self._ptt_active: bool      = False  # SPACE basılı mı

        # Files
        self._files: list[str]      = []

    # ─── State ────────────────────────────────────────────────────────────────
    @property
    def conn_state(self) -> ConnState:
        return self._conn_state

    def set_conn_state(self, state: ConnState | str) -> None:
        if isinstance(state, str):
            try:
                state = ConnState(state)
            except ValueError:
                return
        with self._lock:
            if state == self._conn_state:
                return
            self._conn_state = state
        bus.state_changed.emit(state.value)

    @property
    def muted(self) -> bool:
        return self._muted

    def set_muted(self, value: bool) -> None:
        with self._lock:
            if value == self._muted:
                return
            self._muted = value
        bus.mute_set.emit(value)
        # mute durumu state'i de etkiler — UI'da net olsun
        if value:
            self.set_conn_state(ConnState.MUTED)
        else:
            # unmute: eğer speaking ise SPEAKING'de kal, yoksa LISTENING'e dön
            if self._speaking:
                self.set_conn_state(ConnState.SPEAKING)
            else:
                self.set_conn_state(ConnState.LISTENING)

    @property
    def speaking(self) -> bool:
        return self._speaking

    def set_speaking(self, value: bool) -> None:
        with self._lock:
            if value == self._speaking:
                return
            self._speaking = value
        bus.speaking_set.emit(value)
        if value:
            self.set_conn_state(ConnState.SPEAKING)
        elif not self._muted:
            self.set_conn_state(ConnState.LISTENING)

    # ─── Theme / Performance ──────────────────────────────────────────────────
    @property
    def theme(self) -> Theme:
        return get_theme()

    def set_theme(self, slug: str) -> Theme:
        new_theme = switch_theme(slug)
        # SignalBus üzerinden tüm component'lara duyur
        bus.theme_changed.emit(new_theme)
        return new_theme

    @property
    def perf_level(self) -> PerfLevel:
        return self._perf_level

    def set_perf_level(self, level: PerfLevel | int) -> None:
        if isinstance(level, int):
            try:
                level = PerfLevel(level)
            except ValueError:
                return
        with self._lock:
            if level == self._perf_level:
                return
            self._perf_level = level
        bus.perf_mode_changed.emit(level.value)

    # ─── Input ────────────────────────────────────────────────────────────────
    @property
    def listening_mode(self) -> ListeningMode:
        return self._listening_mode

    def set_listening_mode(self, mode: ListeningMode | str) -> None:
        if isinstance(mode, str):
            try:
                mode = ListeningMode(mode)
            except ValueError:
                return
        with self._lock:
            if mode == self._listening_mode:
                return
            self._listening_mode = mode
        bus.listening_mode_changed.emit(mode.value)

    @property
    def ptt_active(self) -> bool:
        return self._ptt_active

    def set_ptt_active(self, value: bool) -> None:
        with self._lock:
            if value == self._ptt_active:
                return
            self._ptt_active = value
        if value:
            bus.ptt_pressed.emit()
        else:
            bus.ptt_released.emit()

    # ─── Files ────────────────────────────────────────────────────────────────
    @property
    def files(self) -> list[str]:
        with self._lock:
            return list(self._files)

    def add_file(self, path: str) -> None:
        with self._lock:
            if path in self._files:
                return
            self._files.append(path)
        bus.file_added.emit(path)

    def remove_file(self, path: str) -> None:
        with self._lock:
            if path not in self._files:
                return
            self._files.remove(path)
        bus.file_removed.emit(path)

    def clear_files(self) -> None:
        with self._lock:
            if not self._files:
                return
            self._files.clear()
        bus.files_cleared.emit()


# Singleton
state = UIState()


__all__ = ["state", "UIState", "ConnState", "ListeningMode"]
