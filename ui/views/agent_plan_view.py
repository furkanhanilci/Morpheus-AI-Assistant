"""
AgentPlanView — canlı plan ilerleme görüntüleyici.

Görsel:
    ▸ ACTIVE PLAN — "iPhone 17 fiyat araştırması"

    ●─── Step 1 [web_search]      ✓ 2.1s
    │    Search for iPhone 17 launch price
    │
    ●─── Step 2 [file_controller] ⟳ running
    │    Save results to Desktop
    │
    ○─── Step 3 [open_app]        pending
         Open notepad

    [✕ Cancel]

Status simgeleri:
    ✓  ok
    ✗  err
    ⟳  running (rotating, simulate ile dönüyor)
    ○  pending
    ⏭  skip
"""
from __future__ import annotations

import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from ..components import SectionHeader, StyledButton
from ..state import bus
from ..themes import Theme, get_theme


# Visual status mapping
_STATUS_SYMBOLS = {
    "pending": "○",
    "running": "◐",
    "ok":      "●",
    "err":     "●",
    "skip":    "⏭",
}


class StepRow(QWidget):
    """Tek bir plan adımı satırı."""

    def __init__(self, step_num: int, tool: str, description: str,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("StepRow")
        self._step_num = step_num
        self._tool = tool
        self._description = description
        self._status = "pending"
        self._duration_s = 0.0
        self._result = ""
        self._error = ""

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # Status indicator — sol tarafta yuvarlak
        self._status_lbl = QLabel(_STATUS_SYMBOLS["pending"])
        self._status_lbl.setObjectName("StepStatus")
        self._status_lbl.setFixedWidth(18)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._status_lbl)

        # Body — adım metni ve tool etiketi
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(2)

        self._header_lbl = QLabel(f"Step {step_num} · [{tool}]")
        self._header_lbl.setObjectName("StepHeader")
        body_lay.addWidget(self._header_lbl)

        self._desc_lbl = QLabel(description or f"({tool})")
        self._desc_lbl.setObjectName("StepDesc")
        self._desc_lbl.setWordWrap(True)
        body_lay.addWidget(self._desc_lbl)

        lay.addWidget(body, stretch=1)

        # Duration / status text — sağ tarafta
        self._meta_lbl = QLabel("pending")
        self._meta_lbl.setObjectName("StepMeta")
        self._meta_lbl.setFixedWidth(70)
        self._meta_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._meta_lbl)

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def update_status(
        self,
        status: str,
        duration_s: float = 0.0,
        result: str = "",
        error: str = "",
        description: str = "",
    ) -> None:
        self._status = status
        self._duration_s = duration_s
        self._result = result
        self._error = error
        if description:
            self._description = description
            self._desc_lbl.setText(description)

        # Status simgesini ve renk tonunu güncelle
        sym = _STATUS_SYMBOLS.get(status, "?")
        self._status_lbl.setText(sym)

        # Meta text
        if status == "running":
            self._meta_lbl.setText("running…")
        elif status == "ok":
            self._meta_lbl.setText(f"✓ {duration_s:.1f}s")
        elif status == "err":
            self._meta_lbl.setText(f"✗ {duration_s:.1f}s")
        elif status == "skip":
            self._meta_lbl.setText("skipped")
        else:
            self._meta_lbl.setText(status)

        self._apply_theme(get_theme())

    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        # Status color mapping
        status_color_map = {
            "pending": p.text_dim,
            "running": p.secondary,
            "ok":      p.success,
            "err":     p.warning,
            "skip":    p.text_dim,
        }
        status_color = status_color_map.get(self._status, p.text_dim)

        # Background tonu — running daha vurgulu
        if self._status == "running":
            bg = p.secondary_ghost
            border_l = p.secondary
        elif self._status == "ok":
            bg = p.primary_ghost
            border_l = p.primary_dim
        elif self._status == "err":
            bg = "transparent"
            border_l = p.warning
        else:
            bg = "transparent"
            border_l = p.border_dim

        self.setStyleSheet(f"""
            #StepRow {{
                background: {bg};
                border-left: 2px solid {border_l};
                border-radius: {s.radius_sm}px;
                padding: 6px 8px;
                margin-bottom: 4px;
            }}
            #StepStatus {{
                color: {status_color};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_md}pt;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
            #StepHeader {{
                color: {p.text};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
            #StepDesc {{
                color: {p.text_dim};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
                background: transparent;
                border: none;
            }}
            #StepMeta {{
                color: {status_color};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
                background: transparent;
                border: none;
            }}
        """)


class AgentPlanView(QWidget):
    """Plan ilerleme görüntüleyici."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AgentPlanView")

        self._steps: dict[int, StepRow] = {}
        self._current_goal: str = ""
        self._plan_active: bool = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        # Header
        self._header = SectionHeader("ACTIVE PLAN")
        outer.addWidget(self._header)

        # Goal label
        self._goal_lbl = QLabel("")
        self._goal_lbl.setObjectName("PlanGoal")
        self._goal_lbl.setWordWrap(True)
        self._goal_lbl.setVisible(False)
        outer.addWidget(self._goal_lbl)

        # Empty state
        self._empty_lbl = QLabel(
            "No active plan.\n\n"
            "Multi-step tasks will appear here\n"
            "with live progress and step results."
        )
        self._empty_lbl.setObjectName("EmptyLabel")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        outer.addWidget(self._empty_lbl)

        # Scroll area for steps
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(self._scroll.Shape.NoFrame)
        self._scroll.setVisible(False)

        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(2)
        self._content_lay.addStretch()
        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, stretch=1)

        # Cancel + summary row
        action_row = QHBoxLayout()
        self._summary_lbl = QLabel("")
        self._summary_lbl.setObjectName("PlanSummary")
        self._summary_lbl.setWordWrap(True)
        action_row.addWidget(self._summary_lbl, stretch=1)

        self._cancel_btn = StyledButton("✕ Cancel", tone="danger", height=26)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        action_row.addWidget(self._cancel_btn)
        outer.addLayout(action_row)

        # Bus listeners
        bus.plan_started.connect(self._on_plan_started)
        bus.plan_step.connect(self._on_plan_step)
        bus.plan_finished.connect(self._on_plan_finished)
        bus.theme_changed.connect(self._apply_theme)

        self._apply_theme(get_theme())

    # ─── Signal handlers ──────────────────────────────────────────────────────
    def _on_plan_started(self, payload: dict) -> None:
        self._current_goal = payload.get("goal", "")
        steps = payload.get("steps", [])

        # Eski step'leri temizle
        self._clear_steps()
        self._plan_active = True

        # Goal göster
        if self._current_goal:
            self._goal_lbl.setText(f"⟶  {self._current_goal}")
            self._goal_lbl.setVisible(True)

        # Step'leri ekle (pending durumunda)
        for step in steps:
            step_num = step.get("step", len(self._steps) + 1)
            tool = step.get("tool", "unknown")
            desc = step.get("description", "")
            self._add_step(step_num, tool, desc)

        self._empty_lbl.setVisible(False)
        self._scroll.setVisible(True)
        self._cancel_btn.setVisible(True)
        self._summary_lbl.setText("")

    def _on_plan_step(self, payload: dict) -> None:
        step_num = payload.get("step", -1)
        tool = payload.get("tool", "")
        status = payload.get("status", "pending")

        row = self._steps.get(step_num)
        if row is None:
            # Plan başlangıçta gelmediyse, dinamik ekle
            desc = payload.get("description", "")
            row = self._add_step(step_num, tool, desc)

        row.update_status(
            status=status,
            duration_s=payload.get("duration_s", 0.0),
            result=payload.get("result", ""),
            error=payload.get("error", ""),
            description=payload.get("description", ""),
        )

        # Otomatik en alta kaydır (running adımı görünür kalsın)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _on_plan_finished(self, payload: dict) -> None:
        self._plan_active = False
        success = payload.get("success", False)
        summary = payload.get("summary", "")

        if success:
            self._summary_lbl.setText(f"✓ {summary or 'Plan completed.'}")
        else:
            self._summary_lbl.setText(f"✗ {summary or 'Plan failed.'}")

        self._cancel_btn.setVisible(False)

    def _on_cancel(self) -> None:
        bus.plan_cancel_requested.emit()
        bus.log_appended.emit("SYS: plan cancel requested")
        self._cancel_btn.setEnabled(False)

    # ─── Step management ──────────────────────────────────────────────────────
    def _add_step(self, step_num: int, tool: str, description: str) -> StepRow:
        row = StepRow(step_num, tool, description)
        self._steps[step_num] = row
        # Stretch'in önüne ekle
        self._content_lay.insertWidget(self._content_lay.count() - 1, row)
        return row

    def _clear_steps(self) -> None:
        for row in list(self._steps.values()):
            row.setParent(None)
            row.deleteLater()
        self._steps.clear()
        self._cancel_btn.setEnabled(True)

    def _scroll_to_bottom(self) -> None:
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ─── Theming ──────────────────────────────────────────────────────────────
    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        self._goal_lbl.setFont(QFont(t.mono_family, t.size_sm, QFont.Weight.Bold))
        self._goal_lbl.setStyleSheet(
            f"color: {p.primary}; background: transparent; "
            f"border: none; padding: 4px 0;"
        )
        self._empty_lbl.setFont(QFont(t.mono_family, t.size_sm))
        self._empty_lbl.setStyleSheet(
            f"color: {p.text_dim}; background: transparent; padding: 30px 10px;"
        )
        self._summary_lbl.setFont(QFont(t.mono_family, t.size_xs, QFont.Weight.Bold))
        self._summary_lbl.setStyleSheet(
            f"color: {p.text_medium}; background: transparent; "
            f"border: none; padding: 4px 0;"
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


__all__ = ["AgentPlanView", "StepRow"]
