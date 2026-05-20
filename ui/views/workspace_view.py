"""
WorkspaceView — multi-file workspace.

Görsel:
    ▸ WORKSPACE  (3 files loaded)

    📄 thesis_draft.pdf       2.3 MB   ✕
    💻 executor.py            18 KB    ✕
    🖼  hud_mockup.png         450 KB   ✕

    ┌─────────────────────────────────┐
    │   📂  Drop files here           │
    │   or click to browse            │
    └─────────────────────────────────┘

    [Clear all]

Davranış:
  • DropZone halen sağ taraftaki workspace içinde — `state.add_file` aynı.
  • Her dosyanın icon'u uzantısına göre.
  • ✕ ile tek tek silinir; Clear all hepsini.
  • Dosya tıklanırsa: bus.log_appended ile path log'a yazılır.

Backend uyumu:
  • state.files (PR-1'den) — bu view onu render eder.
  • bus.file_added, bus.file_removed, bus.files_cleared dinler.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from ..components import DropZone, SectionHeader, StyledButton
from ..state import bus, state
from ..themes import Theme, get_theme


_ICON_BY_EXT = {
    # Documents
    ".pdf":  "📄", ".doc": "📄", ".docx": "📄", ".odt": "📄",
    ".txt":  "📝", ".md":  "📝", ".rtf":  "📝",
    # Spreadsheets / data
    ".xlsx": "📊", ".xls": "📊", ".csv":  "📊", ".tsv": "📊",
    # Presentations
    ".pptx": "📊", ".ppt": "📊", ".key":  "📊",
    # Code
    ".py":   "💻", ".js":  "💻", ".ts":  "💻", ".tsx": "💻", ".jsx": "💻",
    ".cpp":  "💻", ".c":   "💻", ".h":   "💻", ".hpp": "💻",
    ".java": "💻", ".rs":  "💻", ".go":  "💻", ".rb":  "💻",
    ".sh":   "💻", ".bash": "💻",
    # Web
    ".html": "🌐", ".css": "🎨", ".json": "📋", ".xml": "📋", ".yaml": "📋", ".yml": "📋",
    # Images
    ".png":  "🖼",  ".jpg": "🖼",  ".jpeg": "🖼",  ".gif": "🖼",  ".webp": "🖼",  ".svg": "🖼",
    ".bmp":  "🖼",  ".tiff": "🖼",
    # Audio
    ".mp3":  "🎵", ".wav": "🎵", ".flac": "🎵", ".ogg": "🎵", ".m4a": "🎵",
    # Video
    ".mp4":  "🎬", ".mov": "🎬", ".avi": "🎬", ".mkv": "🎬", ".webm": "🎬",
    # Archives
    ".zip":  "🗜",  ".tar": "🗜",  ".gz":  "🗜",  ".7z":  "🗜",  ".rar": "🗜",
}


def _icon_for(path: str) -> str:
    return _ICON_BY_EXT.get(Path(path).suffix.lower(), "📂")


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


class FileSlot(QWidget):
    """Tek bir dosya satırı."""

    def __init__(self, path: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("FileSlot")
        self._path = path
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 6, 6)
        lay.setSpacing(8)

        self._icon_lbl = QLabel(_icon_for(path))
        self._icon_lbl.setObjectName("SlotIcon")
        self._icon_lbl.setFixedWidth(20)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._icon_lbl)

        # Filename + path tooltip
        p = Path(path)
        self._name_lbl = QLabel(p.name)
        self._name_lbl.setObjectName("SlotName")
        self._name_lbl.setToolTip(str(p))
        lay.addWidget(self._name_lbl, stretch=1)

        # Size
        try:
            size = p.stat().st_size if p.exists() else 0
            size_str = _human_size(size)
        except Exception:
            size_str = "?"
        self._size_lbl = QLabel(size_str)
        self._size_lbl.setObjectName("SlotSize")
        self._size_lbl.setFixedWidth(70)
        self._size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._size_lbl)

        self._remove_btn = StyledButton("✕", tone="ghost", height=24)
        self._remove_btn.setFixedWidth(28)
        self._remove_btn.setToolTip("Remove")
        self._remove_btn.clicked.connect(self._remove)
        lay.addWidget(self._remove_btn)

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def _remove(self):
        state.remove_file(self._path)

    def mouseDoubleClickEvent(self, ev):
        # Çift tıklama → path'i log'a yaz (ileride: dosyayı asistana hatırlatmak için kullanılabilir)
        bus.log_appended.emit(f"FILE: focused → {self._path}")

    def path(self) -> str:
        return self._path

    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography
        s = theme.spacing
        font_sm = QFont(t.mono_family, t.size_xs)
        self._icon_lbl.setFont(QFont(t.mono_family, t.size_md))
        self._name_lbl.setFont(font_sm)
        self._size_lbl.setFont(font_sm)
        self.setStyleSheet(f"""
            #FileSlot {{
                background: {p.panel};
                border: 1px solid {p.border_dim};
                border-radius: {s.radius_sm}px;
            }}
            #FileSlot:hover {{
                background: {p.panel_2};
                border: 1px solid {p.border};
            }}
            #SlotIcon {{
                color: {p.secondary};
                background: transparent; border: none;
            }}
            #SlotName {{
                color: {p.text};
                background: transparent; border: none;
            }}
            #SlotSize {{
                color: {p.text_dim};
                background: transparent; border: none;
            }}
        """)


class WorkspaceView(QWidget):
    """Multi-file workspace."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("WorkspaceView")

        self._slots: dict[str, FileSlot] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        # Header
        self._header = SectionHeader("WORKSPACE")
        outer.addWidget(self._header)

        # Count label
        self._count_lbl = QLabel("No files loaded")
        self._count_lbl.setObjectName("WorkspaceCount")
        outer.addWidget(self._count_lbl)

        # File list — scrollable
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(self._scroll.Shape.NoFrame)
        self._scroll.setMaximumHeight(240)

        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(4)
        self._content_lay.addStretch()
        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll)

        # Drop zone
        self._drop_zone = DropZone(height=84)
        outer.addWidget(self._drop_zone)

        # Bottom actions
        action_row = QHBoxLayout()
        action_row.addStretch()
        self._clear_btn = StyledButton("Clear all", tone="danger", height=24)
        self._clear_btn.clicked.connect(state.clear_files)
        action_row.addWidget(self._clear_btn)
        outer.addLayout(action_row)

        outer.addStretch()

        # Bus listeners
        bus.file_added.connect(self._on_file_added)
        bus.file_removed.connect(self._on_file_removed)
        bus.files_cleared.connect(self._on_files_cleared)
        bus.theme_changed.connect(self._apply_theme)

        self._apply_theme(get_theme())

        # İlk yüklemede mevcut dosyaları sync et
        for path in state.files:
            self._on_file_added(path)
        self._refresh_count()

    # ─── Sync handlers ────────────────────────────────────────────────────────
    def _on_file_added(self, path: str):
        if path in self._slots:
            return
        slot = FileSlot(path)
        self._slots[path] = slot
        # Stretch'in önüne ekle
        self._content_lay.insertWidget(self._content_lay.count() - 1, slot)
        self._refresh_count()

    def _on_file_removed(self, path: str):
        slot = self._slots.pop(path, None)
        if slot is not None:
            slot.setParent(None)
            slot.deleteLater()
        self._refresh_count()

    def _on_files_cleared(self):
        for slot in self._slots.values():
            slot.setParent(None)
            slot.deleteLater()
        self._slots.clear()
        self._refresh_count()

    def _refresh_count(self):
        n = len(self._slots)
        if n == 0:
            self._count_lbl.setText("No files loaded")
            self._clear_btn.setEnabled(False)
        elif n == 1:
            self._count_lbl.setText("1 file in construct")
            self._clear_btn.setEnabled(True)
        else:
            self._count_lbl.setText(f"{n} files in construct")
            self._clear_btn.setEnabled(True)

    # ─── Theming ──────────────────────────────────────────────────────────────
    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography

        self._count_lbl.setFont(QFont(t.mono_family, t.size_xs))
        self._count_lbl.setStyleSheet(
            f"color: {p.text_dim}; background: transparent; "
            f"border: none; padding: 0 2px;"
        )

        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {p.panel}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {p.border}; border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {p.border_bright}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self._content.setStyleSheet("background: transparent;")


__all__ = ["WorkspaceView", "FileSlot"]
