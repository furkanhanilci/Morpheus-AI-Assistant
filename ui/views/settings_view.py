"""
SettingsView — uygulama ayarları.

Bölümler:
  • API & Models    — Gemini API key, model selection
  • Theme           — Morpheus / Mission Control / Minimal radio
  • Performance     — Animation level slider (Off/Low/Normal/High)
  • Input           — Listening mode (Always/PTT/Off), PTT key
  • System          — OS info, version

Tasarım kararları:
  • API key masked input (eye toggle ile göster)
  • Theme switcher canlı — seçince anında değişir
  • Perf slider 4 stop (OFF, LOW, NORMAL, HIGH)
"""
from __future__ import annotations

import platform
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QScrollArea, QVBoxLayout, QWidget,
)

from ..components import SectionHeader, SegmentedControl, StyledButton, Divider
from ..state import bus, state, ListeningMode
from ..themes import PerfLevel, Theme, available_themes, get_theme


# Default API key path — JarvisLive ile uyumlu
import os
_DEFAULT_API_KEY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "config", "api_keys.json"
)


class _Row(QWidget):
    """Tek satır: solda label, sağda widget."""
    def __init__(self, label: str, widget: QWidget, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._label = QLabel(label)
        self._label.setObjectName("SettingsRowLabel")
        self._label.setMinimumWidth(110)
        lay.addWidget(self._label)
        lay.addWidget(widget, stretch=1)
        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography
        self._label.setFont(QFont(t.mono_family, t.size_xs, QFont.Weight.Bold))
        self._label.setStyleSheet(
            f"color: {p.text_dim}; background: transparent; border: none;"
        )


class _SectionGroup(QWidget):
    """SectionHeader + içerik için container — boşluk yönetimi için."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(6)
        self._lay.addWidget(SectionHeader(title))

    def add(self, w: QWidget):
        self._lay.addWidget(w)


class SettingsView(QWidget):
    """
    Settings paneli.

    PR-4'te tek tema (Morpheus) var; PR-5'te 3 tema gelince theme switcher
    otomatik dolacak — `available_themes()` kullanıyoruz.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("SettingsView")

        # Scroll wrapper — uzun ayarlar için
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # ─── API & Models ─────────────────────────────────────────────────────
        api_group = _SectionGroup("API & MODEL")
        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setObjectName("ApiKeyInput")
        self._api_key_input.setPlaceholderText("AIza...")
        self._api_key_input.setText(self._read_api_key())

        api_row_widget = QWidget()
        api_row_lay = QHBoxLayout(api_row_widget)
        api_row_lay.setContentsMargins(0, 0, 0, 0)
        api_row_lay.setSpacing(4)
        api_row_lay.addWidget(self._api_key_input, stretch=1)

        self._show_key_btn = StyledButton("👁", tone="ghost", height=28)
        self._show_key_btn.setFixedWidth(34)
        self._show_key_btn.clicked.connect(self._toggle_key_visibility)
        api_row_lay.addWidget(self._show_key_btn)

        self._save_key_btn = StyledButton("Save", tone="primary", height=28)
        self._save_key_btn.clicked.connect(self._save_api_key)
        api_row_lay.addWidget(self._save_key_btn)

        api_group.add(_Row("Gemini Key", api_row_widget))
        self._api_status = QLabel("")
        self._api_status.setObjectName("ApiStatus")
        api_group.add(self._api_status)
        lay.addWidget(api_group)

        # ─── Theme ────────────────────────────────────────────────────────────
        theme_group = _SectionGroup("THEME")
        theme_options = [(th.slug, th.name) for th in available_themes()]
        # PR-4'te tek tema, ama UI hazır
        self._theme_seg = SegmentedControl(
            segments=theme_options,
            initial=get_theme().slug,
            height=32,
        )
        self._theme_seg.selected.connect(self._on_theme_changed_by_user)
        theme_group.add(self._theme_seg)

        self._theme_desc = QLabel(get_theme().description)
        self._theme_desc.setObjectName("ThemeDescription")
        self._theme_desc.setWordWrap(True)
        theme_group.add(self._theme_desc)
        lay.addWidget(theme_group)

        # ─── Performance ──────────────────────────────────────────────────────
        perf_group = _SectionGroup("PERFORMANCE")
        self._perf_seg = SegmentedControl(
            segments=[
                ("off",    "Off"),
                ("low",    "Low"),
                ("normal", "Normal"),
                ("high",   "High"),
            ],
            initial=self._perf_to_slug(state.perf_level),
            height=30,
        )
        self._perf_seg.selected.connect(self._on_perf_changed_by_user)
        perf_group.add(self._perf_seg)

        self._perf_desc = QLabel(self._perf_description(state.perf_level))
        self._perf_desc.setObjectName("PerfDescription")
        self._perf_desc.setWordWrap(True)
        perf_group.add(self._perf_desc)
        lay.addWidget(perf_group)

        # ─── Input ────────────────────────────────────────────────────────────
        input_group = _SectionGroup("INPUT")
        self._listen_seg = SegmentedControl(
            segments=[
                ("always", "Always"),
                ("ptt",    "PTT (SPACE)"),
                ("off",    "Text Only"),
            ],
            initial=state.listening_mode.value,
            height=30,
        )
        self._listen_seg.selected.connect(self._on_listen_changed_by_user)
        input_group.add(self._listen_seg)
        lay.addWidget(input_group)

        # ─── System ───────────────────────────────────────────────────────────
        sys_group = _SectionGroup("SYSTEM")
        os_label = QLabel(f"OS: {platform.system()} {platform.release()}")
        os_label.setObjectName("InfoLabel")
        sys_group.add(os_label)
        ver_label = QLabel("MARK XXXIX  ·  UI v39.1.0")
        ver_label.setObjectName("InfoLabel")
        sys_group.add(ver_label)
        lay.addWidget(sys_group)

        lay.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # Bus listeners
        bus.theme_changed.connect(self._on_theme_changed_external)
        bus.perf_mode_changed.connect(self._on_perf_changed_external)
        bus.listening_mode_changed.connect(self._on_listen_changed_external)
        bus.theme_changed.connect(self._apply_theme)

        self._apply_theme(get_theme())

    # ─── API key ──────────────────────────────────────────────────────────────
    def _read_api_key(self) -> str:
        try:
            import json
            from pathlib import Path
            p = Path(_DEFAULT_API_KEY_PATH).resolve()
            if p.exists():
                with open(p) as f:
                    data = json.load(f)
                # Backwards compat: küçük harf öncelikli, büyük harf fallback
                return data.get("gemini_api_key", "") or data.get("GEMINI_API_KEY", "")
        except Exception:
            pass
        return ""

    def _save_api_key(self):
        try:
            import json
            from pathlib import Path
            p = Path(_DEFAULT_API_KEY_PATH).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if p.exists():
                try:
                    with open(p) as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            # KÜÇÜK HARF — backend ve actions/ bunu okuyor
            data["gemini_api_key"] = self._api_key_input.text().strip()
            data.pop("GEMINI_API_KEY", None)  # eski alanı temizle
            with open(p, "w") as f:
                json.dump(data, f, indent=2)
            self._api_status.setText("✓ Saved")
            bus.log_appended.emit("SYS: API key saved")
        except Exception as e:
            self._api_status.setText(f"✗ Error: {e}")

    def _toggle_key_visibility(self):
        mode = self._api_key_input.echoMode()
        if mode == QLineEdit.EchoMode.Password:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_key_btn.setText("🙈")
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_key_btn.setText("👁")

    # ─── Theme ────────────────────────────────────────────────────────────────
    def _on_theme_changed_by_user(self, slug: str):
        state.set_theme(slug)

    def _on_theme_changed_external(self, theme: Theme):
        # Settings'ten değil, başka yerden değiştiyse senkronla
        self._theme_seg.set_selected(theme.slug)
        self._theme_desc.setText(theme.description)

    # ─── Perf ─────────────────────────────────────────────────────────────────
    def _perf_to_slug(self, level: PerfLevel) -> str:
        return level.name.lower()

    def _perf_description(self, level: PerfLevel) -> str:
        return {
            PerfLevel.OFF:    "No animations. Static UI, lowest CPU usage.",
            PerfLevel.LOW:    "20 fps. Rain & particles off. Battery-friendly.",
            PerfLevel.NORMAL: "30 fps. Most animations on. Balanced.",
            PerfLevel.HIGH:   "60 fps. All animations on. Best on desktop.",
        }.get(level, "")

    def _on_perf_changed_by_user(self, slug: str):
        mapping = {
            "off":    PerfLevel.OFF,
            "low":    PerfLevel.LOW,
            "normal": PerfLevel.NORMAL,
            "high":   PerfLevel.HIGH,
        }
        level = mapping.get(slug, PerfLevel.HIGH)
        state.set_perf_level(level)
        self._perf_desc.setText(self._perf_description(level))

    def _on_perf_changed_external(self, level_value: int):
        try:
            level = PerfLevel(level_value)
            self._perf_seg.set_selected(self._perf_to_slug(level))
            self._perf_desc.setText(self._perf_description(level))
        except ValueError:
            pass

    # ─── Listening ────────────────────────────────────────────────────────────
    def _on_listen_changed_by_user(self, slug: str):
        try:
            state.set_listening_mode(ListeningMode(slug))
        except ValueError:
            pass

    def _on_listen_changed_external(self, value: str):
        self._listen_seg.set_selected(value)

    # ─── Theming ──────────────────────────────────────────────────────────────
    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        self._theme_desc.setText(theme.description)

        self._api_key_input.setFont(QFont(t.mono_family, t.size_sm))
        self._api_key_input.setStyleSheet(f"""
            #ApiKeyInput {{
                background: {p.dark};
                color: {p.text_strong};
                border: 1px solid {p.border};
                border-radius: {s.radius_sm}px;
                padding: 4px {s.md}px;
                min-height: 22px;
            }}
            #ApiKeyInput:focus {{ border: 1px solid {p.secondary}; }}
        """)

        # Genel container styling
        self.setStyleSheet(f"""
            QWidget#SettingsView {{ background: transparent; }}
            QScrollArea {{ background: transparent; border: none; }}
            #ApiStatus, #ThemeDescription, #PerfDescription, #InfoLabel {{
                color: {p.text_dim};
                background: transparent;
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
                padding: 2px 0;
            }}
            QScrollBar:vertical {{
                background: {p.panel};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {p.border};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {p.border_bright}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)


__all__ = ["SettingsView"]
