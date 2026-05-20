"""
RightDock — sağ panelin tamamı.

Yapı:
  ┌─────────────────────────────────┐
  │  [💬] [🧩] [⚡] [🧠] [📂] [⚙]  │  ← TabBar
  ├─────────────────────────────────┤
  │                                 │
  │     Aktif sekmenin içeriği      │  ← QStackedWidget
  │                                 │
  └─────────────────────────────────┘

QStackedWidget pattern: tüm view'lar oluşturulur, biri görünür diğerleri saklı.
Sekme değişiminde currentIndex set edilir — view yeniden oluşturulmaz.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from ..components.tab_bar import TabBar
from ..state import bus
from ..themes import Theme, get_theme

from .agent_plan_view import AgentPlanView
from .conversation_view import ConversationView
from .memory_inspector import MemoryInspectorView
from .settings_view import SettingsView
from .tool_activity_view import ToolActivityView
from .workspace_view import WorkspaceView


# Tab tanımı: (key, icon, tooltip, view_factory)
_TAB_KEYS = [
    ("chat",     "💬", "Chat"),
    ("plan",     "🧩", "Agent Plan"),
    ("tools",    "⚡", "Tool Activity"),
    ("memory",   "🧠", "Memory Inspector"),
    ("files",    "📂", "Files Workspace"),
    ("settings", "⚙",  "Settings"),
]


class RightDock(QWidget):
    """Sağ panel: tab bar + stacked content."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("RightDock")
        th = get_theme()
        self.setFixedWidth(th.spacing.right_dock_w)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ─── Tab bar ──────────────────────────────────────────────────────────
        self._tab_bar = TabBar(
            tabs=[(k, ic, tip) for k, ic, tip in _TAB_KEYS],
            initial="chat",
        )
        self._tab_bar.tab_changed.connect(self._on_tab_changed)
        outer.addWidget(self._tab_bar)

        # ─── Stacked content ──────────────────────────────────────────────────
        self._stack = QStackedWidget()

        self._views: dict[str, QWidget] = {
            "chat":     ConversationView(),
            "plan":     AgentPlanView(),
            "tools":    ToolActivityView(),
            "memory":   MemoryInspectorView(),
            "files":    WorkspaceView(),
            "settings": SettingsView(),
        }
        self._indices: dict[str, int] = {}
        for key, _, _ in _TAB_KEYS:
            idx = self._stack.addWidget(self._wrap_padding(self._views[key]))
            self._indices[key] = idx

        outer.addWidget(self._stack, stretch=1)

        # Bus listeners — plan running olduğunda plan tab'ına badge ekle
        bus.plan_started.connect(lambda _: self._tab_bar.set_badge("plan", True))
        bus.plan_finished.connect(lambda _: self._tab_bar.set_badge("plan", False))

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def _wrap_padding(self, view: QWidget) -> QWidget:
        """Her view'a tema spacing'ine göre padding ekle."""
        th = get_theme()
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(th.spacing.lg, th.spacing.lg,
                               th.spacing.lg, th.spacing.lg)
        lay.setSpacing(th.spacing.md)
        lay.addWidget(view)
        return wrap

    def _on_tab_changed(self, key: str):
        idx = self._indices.get(key)
        if idx is not None:
            self._stack.setCurrentIndex(idx)

    def set_active_tab(self, key: str):
        """Programatik tab switching — ör. kullanıcı 'Cmd+,' basınca Settings'e."""
        self._tab_bar.set_active(key)

    def _apply_theme(self, theme: Theme):
        p = theme.palette
        self.setFixedWidth(theme.spacing.right_dock_w)
        self.setStyleSheet(f"""
            #RightDock {{
                background: {p.dark};
                border-left: 1px solid {p.border};
            }}
        """)


__all__ = ["RightDock"]
