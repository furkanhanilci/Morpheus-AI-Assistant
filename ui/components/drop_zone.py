"""
DropZone — dosya yükleme alanı.

PR-2'de minimal: animasyonsuz, sadece çalışan davranış.
PR-3'te animasyonlu canvas (dashed border, hover halo) eklenir.

Multi-file destekli: drop edilen her dosya state.add_file() ile eklenir,
bus.file_added emit edilir. Yükleme sınırı yok.

Görsel:
    ┌─────────────────────────┐
    │   📂  Drop files here   │
    │   or click to browse    │
    └─────────────────────────┘
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtWidgets import QFileDialog, QLabel, QVBoxLayout, QWidget

from ..state import bus, state
from ..themes import Theme, get_theme


class DropZone(QWidget):
    """
    Drag & drop + click-to-browse multi-file zone.
    Drop edilen dosyaları state.add_file() üzerinden global state'e gönderir.
    """

    files_dropped = pyqtSignal(list)  # [path1, path2, ...]

    def __init__(self, height: int = 80, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(height)

        self._hovering = False
        self._dragging = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(2)

        self._icon_label = QLabel("📂")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setObjectName("DropZoneIcon")
        lay.addWidget(self._icon_label)

        self._hint_label = QLabel("Drop files here\nor click to browse")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setObjectName("DropZoneHint")
        self._hint_label.setWordWrap(True)
        lay.addWidget(self._hint_label)

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    # ─── Events ───────────────────────────────────────────────────────────────
    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._dragging = True
            self._apply_theme(get_theme())

    def dragLeaveEvent(self, _e) -> None:
        self._dragging = False
        self._apply_theme(get_theme())

    def dropEvent(self, e: QDropEvent) -> None:
        self._dragging = False
        paths: list[str] = []
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if p and Path(p).is_file():
                paths.append(p)
        for p in paths:
            state.add_file(p)
        if paths:
            self.files_dropped.emit(paths)
        self._apply_theme(get_theme())

    def enterEvent(self, _e) -> None:
        self._hovering = True
        self._apply_theme(get_theme())

    def leaveEvent(self, _e) -> None:
        self._hovering = False
        self._apply_theme(get_theme())

    def mousePressEvent(self, e) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select file(s) to load",
            str(Path.home()),
            "All Files (*.*)",
        )
        if not paths:
            return
        for p in paths:
            state.add_file(p)
        self.files_dropped.emit(paths)

    # ─── Theming ──────────────────────────────────────────────────────────────
    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        if self._dragging:
            border_col = p.primary
            bg_col     = p.primary_ghost
            hint_col   = p.primary
        elif self._hovering:
            border_col = p.secondary
            bg_col     = p.secondary_ghost
            hint_col   = p.text
        else:
            border_col = p.border
            bg_col     = p.panel
            hint_col   = p.text_dim

        self.setStyleSheet(f"""
            #DropZone {{
                background: {bg_col};
                border: 1px dashed {border_col};
                border-radius: {s.radius_md}px;
            }}
            #DropZoneIcon {{
                color: {hint_col};
                font-size: {t.size_xl}pt;
                background: transparent;
                border: none;
            }}
            #DropZoneHint {{
                color: {hint_col};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
                background: transparent;
                border: none;
            }}
        """)


__all__ = ["DropZone"]
