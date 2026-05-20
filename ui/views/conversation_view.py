"""
ConversationView — user/AI mesajlarını kart olarak gösterir.

Görsel:
    ▸ CONVERSATION

    You · 14:23
    ┌─────────────────────────────────┐
    │ Karsan motion stack'i özetle    │
    └─────────────────────────────────┘

    Morpheus · 14:23
    ┌─────────────────────────────────┐
    │ The Karsan motion stack runs on │
    │ ROS2 with a custom motion       │
    │ planner...                       │
    └─────────────────────────────────┘
     [📋 Copy]  [🔄 Regenerate]

Backend bağlantısı:
  bus.user_message.emit("...")  → bu view dinler, kullanıcı kartı ekler
  bus.ai_message.emit("...")    → asistan kartı ekler
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QClipboard, QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from ..components import SectionHeader, StyledButton
from ..state import bus
from ..themes import Theme, get_theme


@dataclass
class Message:
    role: str          # "user" | "ai"
    text: str
    ts: float          # epoch seconds
    tool_calls: list[str] = None  # AI message için kullanılan tool'lar


class MessageCard(QWidget):
    """Tek bir mesaj için kart widget'ı."""

    def __init__(self, msg: Message, on_copy=None, on_regenerate=None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._msg = msg
        self._on_copy = on_copy
        self._on_regenerate = on_regenerate
        self.setObjectName("MessageCard")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        # Header: rol + zaman
        ts_str = time.strftime("%H:%M", time.localtime(msg.ts))
        role_label = "You" if msg.role == "user" else "Morpheus"
        self._header = QLabel(f"{role_label} · {ts_str}")
        self._header.setObjectName("CardHeader")
        lay.addWidget(self._header)

        # Body — bubble
        self._body = QLabel(msg.text)
        self._body.setObjectName("CardBody")
        self._body.setWordWrap(True)
        self._body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self._body)

        # Tool badges (AI message için)
        if msg.role == "ai" and msg.tool_calls:
            badges = QLabel("🔧 " + ", ".join(msg.tool_calls))
            badges.setObjectName("CardBadges")
            lay.addWidget(badges)

        # Actions (AI message için)
        if msg.role == "ai":
            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(0, 4, 0, 0)
            al.setSpacing(4)

            self._copy_btn = StyledButton("📋 Copy", tone="ghost", height=24)
            self._copy_btn.clicked.connect(self._handle_copy)
            al.addWidget(self._copy_btn)

            self._regen_btn = StyledButton("🔄 Regen", tone="ghost", height=24)
            self._regen_btn.clicked.connect(self._handle_regen)
            al.addWidget(self._regen_btn)

            al.addStretch()
            lay.addWidget(actions)

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def _handle_copy(self):
        clip = QGuiApplication.clipboard()
        if clip:
            clip.setText(self._msg.text)
        if self._on_copy:
            self._on_copy(self._msg)

    def _handle_regen(self):
        if self._on_regenerate:
            self._on_regenerate(self._msg)

    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        # User mesajı = secondary tonu, AI = primary tonu
        if self._msg.role == "user":
            body_bg = p.secondary_ghost
            body_border = p.secondary_dim
            body_color = p.text
        else:
            body_bg = p.primary_ghost
            body_border = p.primary_dim
            body_color = p.text_strong

        self._header.setFont(QFont(t.mono_family, t.size_xs, QFont.Weight.Bold))
        self._header.setStyleSheet(
            f"color: {p.text_dim}; background: transparent; "
            f"border: none; padding: 2px 0;"
        )

        self._body.setFont(QFont(t.mono_family, t.size_sm))
        self._body.setStyleSheet(f"""
            #CardBody {{
                background: {body_bg};
                color: {body_color};
                border: 1px solid {body_border};
                border-radius: {s.radius_md}px;
                padding: {s.md}px {s.lg}px;
            }}
        """)


class ConversationView(QWidget):
    """Mesaj listesi — scrollable, bus.user_message ve bus.ai_message dinler."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ConversationView")
        self._messages: list[Message] = []

        # Outer layout: header + scroll area
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        outer.addWidget(SectionHeader("CONVERSATION"))

        self._empty_label = QLabel("No messages yet. Speak or type to begin.")
        self._empty_label.setObjectName("EmptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._empty_label)

        # Scroll area + content widget
        self._scroll = QScrollArea()
        self._scroll.setObjectName("ConversationScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(self._scroll.Shape.NoFrame)

        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(12)
        self._content_lay.addStretch()  # son eleman = stretch (mesajlar üstte birikir)

        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, stretch=1)

        # Bus listeners
        bus.user_message.connect(self._on_user_message)
        bus.ai_message.connect(self._on_ai_message)
        bus.theme_changed.connect(self._apply_theme)

        self._apply_theme(get_theme())
        self._refresh_empty()

    def _on_user_message(self, text: str):
        self._add_message(Message(role="user", text=text, ts=time.time()))

    def _on_ai_message(self, text: str):
        self._add_message(Message(role="ai", text=text, ts=time.time()))

    def _add_message(self, msg: Message):
        self._messages.append(msg)
        card = MessageCard(msg,
                           on_copy=self._on_copy,
                           on_regenerate=self._on_regenerate)
        # Stretch'in önüne ekle (en alta)
        self._content_lay.insertWidget(self._content_lay.count() - 1, card)
        self._refresh_empty()

        # Otomatik en alta kaydır
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_copy(self, msg: Message):
        bus.log_appended.emit(f"SYS: copied AI message to clipboard ({len(msg.text)} chars)")

    def _on_regenerate(self, msg: Message):
        # En son user message'ı bul, indeksi gönder
        for i in range(len(self._messages) - 1, -1, -1):
            if self._messages[i].role == "user":
                bus.regenerate_requested.emit(i)
                bus.log_appended.emit(f"SYS: regenerate requested")
                return

    def _refresh_empty(self):
        self._empty_label.setVisible(len(self._messages) == 0)
        self._scroll.setVisible(len(self._messages) > 0)

    def clear(self):
        for i in reversed(range(self._content_lay.count() - 1)):
            item = self._content_lay.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self._messages.clear()
        self._refresh_empty()

    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography
        self._empty_label.setFont(QFont(t.mono_family, t.size_sm))
        self._empty_label.setStyleSheet(
            f"color: {p.text_dim}; background: transparent; padding: 20px;"
        )
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
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
        self._content.setStyleSheet("background: transparent;")


__all__ = ["ConversationView", "Message"]
