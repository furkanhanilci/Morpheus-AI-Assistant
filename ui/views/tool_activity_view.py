"""
ToolActivityView — tool çağrı feed'i.

Görsel:
    ▸ TOOL ACTIVITY                  [Clear] [Export]

    14:23:01  web_search        ⟳
    14:23:03  web_search        ✓ 2.1s
    14:24:15  file_controller   ✓ 0.3s
    14:24:20  open_app          ✗ 0.5s  "App not found"
    14:25:02  screen_process    ⟳
    14:25:04  screen_process    ✓ 1.8s

Her tool çağrısı bus.tool_started ile satır olarak başlar, bus.tool_finished ile
status + duration alır.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from ..components import SectionHeader, StyledButton
from ..state import bus
from ..themes import Theme, get_theme


@dataclass
class ToolEvent:
    name:       str
    params:     dict
    started_ts: float
    finished_ts: float = 0.0
    duration_s: float  = 0.0
    ok:         bool   = True
    result:     str    = ""
    error:      str    = ""
    running:    bool   = True


class _ToolRow(QWidget):
    """Tek bir tool çağrısı satırı."""

    def __init__(self, event: ToolEvent, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ToolRow")
        self._event = event

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # Timestamp
        ts_str = time.strftime("%H:%M:%S", time.localtime(event.started_ts))
        self._ts_lbl = QLabel(ts_str)
        self._ts_lbl.setObjectName("ToolTs")
        self._ts_lbl.setFixedWidth(64)
        lay.addWidget(self._ts_lbl)

        # Tool name
        self._name_lbl = QLabel(event.name)
        self._name_lbl.setObjectName("ToolName")
        lay.addWidget(self._name_lbl, stretch=1)

        # Status + duration
        self._meta_lbl = QLabel("⟳")
        self._meta_lbl.setObjectName("ToolMeta")
        self._meta_lbl.setFixedWidth(70)
        self._meta_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._meta_lbl)

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def finalize(self, ok: bool, duration_s: float, error: str = "") -> None:
        self._event.running = False
        self._event.ok = ok
        self._event.duration_s = duration_s
        self._event.error = error
        if ok:
            self._meta_lbl.setText(f"✓ {duration_s:.1f}s")
        else:
            self._meta_lbl.setText(f"✗ {duration_s:.1f}s")
            if error:
                # Hata kısaltıp tooltip'e koy
                self.setToolTip(error[:240])
        self._apply_theme(get_theme())

    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography

        if self._event.running:
            meta_color = p.secondary
        elif self._event.ok:
            meta_color = p.success
        else:
            meta_color = p.warning

        font = QFont(t.mono_family, t.size_xs)
        self._ts_lbl.setFont(font)
        self._name_lbl.setFont(font)
        self._meta_lbl.setFont(font)

        self.setStyleSheet(f"""
            #ToolRow {{
                background: transparent;
                border-bottom: 1px solid {p.border_dim};
                padding: 4px 0;
            }}
            #ToolTs {{
                color: {p.text_dim};
                background: transparent; border: none;
            }}
            #ToolName {{
                color: {p.text};
                background: transparent; border: none;
            }}
            #ToolMeta {{
                color: {meta_color};
                background: transparent; border: none;
                font-weight: bold;
            }}
        """)


class ToolActivityView(QWidget):
    """Tool çağrılarının kronolojik log'u."""

    MAX_EVENTS = 200  # bellek koruması

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ToolActivityView")

        self._events: list[ToolEvent] = []
        self._rows: list[_ToolRow] = []
        # Aktif (running) tool'ları index'le (name → row index) — basit map
        self._running: dict[str, _ToolRow] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        # Header + action row
        header_row = QHBoxLayout()
        header_row.addWidget(SectionHeader("TOOL ACTIVITY"), stretch=1)
        self._clear_btn = StyledButton("Clear", tone="ghost", height=22)
        self._clear_btn.clicked.connect(self.clear)
        header_row.addWidget(self._clear_btn)
        self._export_btn = StyledButton("Export", tone="ghost", height=22)
        self._export_btn.clicked.connect(self._export_json)
        header_row.addWidget(self._export_btn)
        outer.addLayout(header_row)

        # Empty state
        self._empty_lbl = QLabel(
            "No tool calls yet.\n\n"
            "Every tool invocation will appear here\n"
            "with timing and outcome."
        )
        self._empty_lbl.setObjectName("EmptyLabel")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        outer.addWidget(self._empty_lbl)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(self._scroll.Shape.NoFrame)
        self._scroll.setVisible(False)

        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(0)
        self._content_lay.addStretch()
        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, stretch=1)

        # Bus listeners
        bus.tool_started.connect(self._on_tool_started)
        bus.tool_finished.connect(self._on_tool_finished)
        bus.theme_changed.connect(self._apply_theme)

        self._apply_theme(get_theme())

    # ─── Signal handlers ──────────────────────────────────────────────────────
    def _on_tool_started(self, tool_name: str, params: dict) -> None:
        ev = ToolEvent(
            name=tool_name,
            params=dict(params) if params else {},
            started_ts=time.time(),
        )
        self._events.append(ev)
        row = _ToolRow(ev)
        self._rows.append(row)
        self._content_lay.insertWidget(self._content_lay.count() - 1, row)

        # Running map: aynı tool birden fazla kez çalışırsa son başlayanı tut
        self._running[tool_name] = row

        # Eski event'leri kırp
        self._enforce_cap()

        self._empty_lbl.setVisible(False)
        self._scroll.setVisible(True)
        # Auto-scroll
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(30, self._scroll_to_bottom)

    def _on_tool_finished(self, tool_name: str, info: dict) -> None:
        row = self._running.pop(tool_name, None)
        if row is None:
            # Eşleşme yoksa görmezden gel
            return
        row.finalize(
            ok=bool(info.get("ok", True)),
            duration_s=float(info.get("duration_s", 0.0)),
            error=str(info.get("error", "")),
        )

    # ─── Actions ──────────────────────────────────────────────────────────────
    def clear(self) -> None:
        for row in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        self._events.clear()
        self._running.clear()
        self._empty_lbl.setVisible(True)
        self._scroll.setVisible(False)

    def _export_json(self) -> None:
        if not self._events:
            bus.log_appended.emit("SYS: no tool events to export")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export tool activity",
            "tool_activity.json", "JSON (*.json)"
        )
        if not path:
            return
        data = [
            {
                "name":       ev.name,
                "started":    ev.started_ts,
                "duration_s": ev.duration_s,
                "ok":         ev.ok,
                "result":     ev.result,
                "error":      ev.error,
                "params":     ev.params,
            }
            for ev in self._events
        ]
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            bus.log_appended.emit(f"SYS: exported {len(data)} events to {path}")
        except Exception as e:
            bus.log_appended.emit(f"SYS: export failed — {e}")

    def _enforce_cap(self) -> None:
        # En eski satırları sil
        while len(self._rows) > self.MAX_EVENTS:
            row = self._rows.pop(0)
            self._events.pop(0)
            row.setParent(None)
            row.deleteLater()

    def _scroll_to_bottom(self) -> None:
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ─── Theming ──────────────────────────────────────────────────────────────
    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography

        self._empty_lbl.setFont(QFont(t.mono_family, t.size_sm))
        self._empty_lbl.setStyleSheet(
            f"color: {p.text_dim}; background: transparent; padding: 30px 10px;"
        )
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {p.panel}; width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {p.border}; border-radius: 4px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {p.border_bright}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self._content.setStyleSheet("background: transparent;")


__all__ = ["ToolActivityView"]
