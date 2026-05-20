"""
MemoryInspectorView — long_term.json browse + edit.

Görsel:
    ▸ LONG-TERM MEMORY        [🔍 Search] [Export] [Reload]

    ▾ identity                                              [+ Add]
       full_name        Furkan Hanilçi                  ✎  🗑
       location_city    Bursa                            ✎  🗑
       job              Karsan Otomotiv R&D Engineer    ✎  🗑

    ▸ projects (4)
    ▸ preferences (12)
    ▸ publications (3)
    ▸ notes (8)

Davranış:
  • Kategoriler collapsible. Default: identity açık, diğerleri kapalı.
  • ✎ inline edit modu — entry value editlenir.
  • 🗑 confirm dialog ile sil.
  • [+ Add] kategoriye yeni entry ekle.
  • Search — tüm kategorilerde key + value içinde filtre.
  • Reload — diskten tekrar oku.
  • Export — JSON dosyası olarak diske kaydet.
  • Reset — TÜM memory'yi siler (çift onay).

Backend ile uyum:
  • memory/memory_manager.py'ın load_memory(), save_memory(), forget() çağrılır.
  • Backend yoksa salt-okunur fallback'le çalışır.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QScrollArea, QVBoxLayout, QWidget,
)

from ..components import SectionHeader, StyledButton
from ..state import bus
from ..themes import Theme, get_theme


# ─── Memory backend bağlantısı ────────────────────────────────────────────────
# Backend varsa onu kullan, yoksa fallback (UI-only test için)
def _find_memory_path() -> Path:
    """Project root'taki memory/long_term.json'u bul."""
    here = Path(__file__).resolve()
    for parent in [here.parent.parent.parent, here.parent.parent.parent.parent]:
        candidate = parent / "memory" / "long_term.json"
        if candidate.exists():
            return candidate
    # Yoksa default — yazılabilir hali olmasını sağlamak için yine bunu döndür
    return here.parent.parent.parent / "memory" / "long_term.json"


_MEMORY_PATH = _find_memory_path()


def _load_memory_safe() -> dict:
    """Backend varsa onu kullan, yoksa direkt dosyadan oku."""
    try:
        # Backend bağlantısı
        sys.path.insert(0, str(_MEMORY_PATH.parent.parent))
        from memory.memory_manager import load_memory
        return load_memory()
    except Exception:
        # Fallback — direkt dosya
        if _MEMORY_PATH.exists():
            try:
                return json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}


def _save_memory_safe(memory: dict) -> bool:
    """Backend varsa onu kullan, yoksa direkt yaz."""
    try:
        sys.path.insert(0, str(_MEMORY_PATH.parent.parent))
        from memory.memory_manager import save_memory
        save_memory(memory)
        return True
    except Exception:
        try:
            _MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            _MEMORY_PATH.write_text(
                json.dumps(memory, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return True
        except Exception as e:
            print(f"[MemoryInspector] save error: {e}")
            return False


# ─── Entry row (tek bir key/value) ────────────────────────────────────────────
class EntryRow(QWidget):
    """Tek bir memory entry için satır."""

    edit_requested   = pyqtSignal(str, str)  # (category, key)
    delete_requested = pyqtSignal(str, str)

    def __init__(self, category: str, key: str, value: str, updated: str = "",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("EntryRow")
        self._category = category
        self._key = key
        self._value = value
        self._updated = updated
        self._editing = False

        # Layout
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(16, 4, 4, 4)
        self._lay.setSpacing(8)

        self._key_lbl = QLabel(self._format_key(key))
        self._key_lbl.setObjectName("EntryKey")
        self._key_lbl.setFixedWidth(120)
        self._lay.addWidget(self._key_lbl)

        # Value: read mode QLabel ya da edit mode QLineEdit
        self._value_lbl = QLabel(self._truncate(value))
        self._value_lbl.setObjectName("EntryValue")
        self._value_lbl.setWordWrap(True)
        self._value_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if updated:
            self._value_lbl.setToolTip(f"Updated: {updated}")
        self._lay.addWidget(self._value_lbl, stretch=1)

        self._value_edit = QLineEdit()
        self._value_edit.setObjectName("EntryEdit")
        self._value_edit.setVisible(False)
        self._lay.addWidget(self._value_edit, stretch=1)

        # Action buttons
        self._edit_btn = StyledButton("✎", tone="ghost", height=22)
        self._edit_btn.setFixedWidth(28)
        self._edit_btn.setToolTip("Edit")
        self._edit_btn.clicked.connect(self._enter_edit_mode)
        self._lay.addWidget(self._edit_btn)

        self._save_btn = StyledButton("✓", tone="primary", height=22)
        self._save_btn.setFixedWidth(28)
        self._save_btn.setVisible(False)
        self._save_btn.clicked.connect(self._save_edit)
        self._lay.addWidget(self._save_btn)

        self._cancel_btn = StyledButton("✕", tone="ghost", height=22)
        self._cancel_btn.setFixedWidth(28)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._cancel_edit)
        self._lay.addWidget(self._cancel_btn)

        self._delete_btn = StyledButton("🗑", tone="ghost", height=22)
        self._delete_btn.setFixedWidth(28)
        self._delete_btn.setToolTip("Delete")
        self._delete_btn.clicked.connect(lambda: self.delete_requested.emit(category, key))
        self._lay.addWidget(self._delete_btn)

        # Edit modunda Enter ile save, Esc ile cancel
        self._value_edit.returnPressed.connect(self._save_edit)

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def _format_key(self, key: str) -> str:
        return key.replace("_", " ").title()

    def _truncate(self, val: str, n: int = 100) -> str:
        if not val:
            return "(empty)"
        if len(val) > n:
            return val[:n - 1] + "…"
        return val

    def _enter_edit_mode(self):
        self._editing = True
        self._value_edit.setText(self._value)
        self._value_lbl.setVisible(False)
        self._value_edit.setVisible(True)
        self._edit_btn.setVisible(False)
        self._delete_btn.setVisible(False)
        self._save_btn.setVisible(True)
        self._cancel_btn.setVisible(True)
        self._value_edit.setFocus()
        self._value_edit.selectAll()

    def _save_edit(self):
        new_val = self._value_edit.text().strip()
        if not new_val:
            self._cancel_edit()
            return
        self._value = new_val
        self.edit_requested.emit(self._category, self._key)
        self._exit_edit_mode()

    def _cancel_edit(self):
        self._exit_edit_mode()

    def _exit_edit_mode(self):
        self._editing = False
        self._value_lbl.setText(self._truncate(self._value))
        self._value_lbl.setVisible(True)
        self._value_edit.setVisible(False)
        self._edit_btn.setVisible(True)
        self._delete_btn.setVisible(True)
        self._save_btn.setVisible(False)
        self._cancel_btn.setVisible(False)

    def new_value(self) -> str:
        return self._value

    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography
        s = theme.spacing
        font = QFont(t.mono_family, t.size_xs)
        self._key_lbl.setFont(font)
        self._value_lbl.setFont(font)
        self._value_edit.setFont(font)
        self.setStyleSheet(f"""
            #EntryRow {{
                background: transparent;
                border-radius: {s.radius_sm}px;
            }}
            #EntryRow:hover {{
                background: {p.panel_2};
            }}
            #EntryKey {{
                color: {p.secondary};
                background: transparent; border: none;
            }}
            #EntryValue {{
                color: {p.text};
                background: transparent; border: none;
            }}
            #EntryEdit {{
                background: {p.dark};
                color: {p.text_strong};
                border: 1px solid {p.secondary};
                border-radius: {s.radius_sm}px;
                padding: 2px {s.sm}px;
            }}
        """)


# ─── Category section ─────────────────────────────────────────────────────────
class CategorySection(QWidget):
    """
    Genişletilebilir kategori bölümü.

      ▾ identity                                  [+ Add]
         (entries...)
    """

    add_requested    = pyqtSignal(str)               # category
    edit_requested   = pyqtSignal(str, str, str)     # (category, key, new_value)
    delete_requested = pyqtSignal(str, str)          # (category, key)

    def __init__(self, category: str, entries: dict, expanded: bool = False,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("CategorySection")
        self._category = category
        self._entries = entries
        self._expanded = expanded
        self._rows: list[EntryRow] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header row
        header = QWidget()
        header.setObjectName("CategoryHeader")
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(0, 4, 4, 4)
        h_lay.setSpacing(4)

        self._arrow_lbl = QLabel("▾" if expanded else "▸")
        self._arrow_lbl.setObjectName("CategoryArrow")
        self._arrow_lbl.setFixedWidth(14)
        h_lay.addWidget(self._arrow_lbl)

        self._title_lbl = QLabel(f"{category}  ({len(entries)})")
        self._title_lbl.setObjectName("CategoryTitle")
        h_lay.addWidget(self._title_lbl, stretch=1)

        self._add_btn = StyledButton("+ Add", tone="ghost", height=22)
        self._add_btn.setFixedWidth(60)
        self._add_btn.clicked.connect(lambda: self.add_requested.emit(self._category))
        h_lay.addWidget(self._add_btn)

        header.mousePressEvent = self._on_header_clicked
        outer.addWidget(header)

        # Entries container
        self._entries_widget = QWidget()
        self._entries_lay = QVBoxLayout(self._entries_widget)
        self._entries_lay.setContentsMargins(0, 0, 0, 4)
        self._entries_lay.setSpacing(0)
        self._entries_widget.setVisible(expanded)
        outer.addWidget(self._entries_widget)

        # Entry satırlarını ekle
        self._build_entries()

        bus.theme_changed.connect(self._apply_theme)
        self._apply_theme(get_theme())

    def _build_entries(self):
        # Önce mevcut row'ları temizle
        for row in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()

        # Sort entries alfabetik
        for key in sorted(self._entries.keys()):
            entry = self._entries[key]
            if isinstance(entry, dict):
                value = entry.get("value", "")
                updated = entry.get("updated", "")
            else:
                value = str(entry)
                updated = ""
            row = EntryRow(self._category, key, value, updated)
            row.edit_requested.connect(self._handle_row_edit)
            row.delete_requested.connect(self.delete_requested.emit)
            self._rows.append(row)
            self._entries_lay.addWidget(row)

    def _handle_row_edit(self, category: str, key: str):
        # Row kendi içinde yeni değeri tutuyor — kim emit'liyorsa o
        for row in self._rows:
            if row._key == key:
                self.edit_requested.emit(category, key, row.new_value())
                return

    def _on_header_clicked(self, _ev):
        self.set_expanded(not self._expanded)

    def set_expanded(self, value: bool):
        self._expanded = value
        self._arrow_lbl.setText("▾" if value else "▸")
        self._entries_widget.setVisible(value)

    def update_entries(self, entries: dict):
        self._entries = entries
        self._title_lbl.setText(f"{self._category}  ({len(entries)})")
        self._build_entries()

    def matches_filter(self, query: str) -> bool:
        """Search filtresi için: kategori adı veya bir entry içerik ile eşleşiyor mu?"""
        if not query:
            return True
        q = query.lower()
        if q in self._category.lower():
            return True
        for key, entry in self._entries.items():
            if q in key.lower():
                return True
            val = entry.get("value", "") if isinstance(entry, dict) else str(entry)
            if q in val.lower():
                return True
        return False

    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography
        s = theme.spacing
        self._arrow_lbl.setFont(QFont(t.mono_family, t.size_sm, QFont.Weight.Bold))
        self._title_lbl.setFont(QFont(t.mono_family, t.size_sm, QFont.Weight.Bold))
        self.setStyleSheet(f"""
            #CategoryHeader {{
                background: {p.panel};
                border-radius: {s.radius_sm}px;
            }}
            #CategoryHeader:hover {{
                background: {p.panel_2};
            }}
            #CategoryArrow {{
                color: {p.text_dim};
                background: transparent; border: none;
                padding: 2px 4px;
            }}
            #CategoryTitle {{
                color: {p.primary};
                background: transparent; border: none;
            }}
        """)


# ─── Main view ────────────────────────────────────────────────────────────────
class MemoryInspectorView(QWidget):
    """Long-term memory editor."""

    # Default expanded category
    _DEFAULT_EXPANDED = {"identity"}

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("MemoryInspectorView")

        self._memory: dict = {}
        self._sections: dict[str, CategorySection] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        # ─── Header row ───────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.addWidget(SectionHeader("LONG-TERM MEMORY"), stretch=1)

        self._reload_btn = StyledButton("Reload", tone="ghost", height=22)
        self._reload_btn.clicked.connect(self.reload)
        header_row.addWidget(self._reload_btn)

        self._export_btn = StyledButton("Export", tone="ghost", height=22)
        self._export_btn.clicked.connect(self._export_json)
        header_row.addWidget(self._export_btn)

        outer.addLayout(header_row)

        # ─── Search bar ───────────────────────────────────────────────────────
        self._search_input = QLineEdit()
        self._search_input.setObjectName("MemorySearch")
        self._search_input.setPlaceholderText("🔍 Search keys and values…")
        self._search_input.textChanged.connect(self._on_search_changed)
        outer.addWidget(self._search_input)

        # ─── Status label (entry counts, save feedback) ───────────────────────
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("MemoryStatus")
        outer.addWidget(self._status_lbl)

        # ─── Scrollable category list ─────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(self._scroll.Shape.NoFrame)

        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(2)
        self._content_lay.addStretch()
        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, stretch=1)

        # ─── Bottom toolbar — bulk actions ────────────────────────────────────
        bottom = QHBoxLayout()
        self._add_cat_btn = StyledButton("+ Category", tone="ghost", height=24)
        self._add_cat_btn.clicked.connect(self._add_category)
        bottom.addWidget(self._add_cat_btn)
        bottom.addStretch()
        self._reset_btn = StyledButton("Reset All", tone="danger", height=24)
        self._reset_btn.clicked.connect(self._reset_all)
        bottom.addWidget(self._reset_btn)
        outer.addLayout(bottom)

        bus.theme_changed.connect(self._apply_theme)
        bus.memory_updated.connect(self._on_memory_updated_external)

        self._apply_theme(get_theme())
        self.reload()

    # ─── Load/refresh ─────────────────────────────────────────────────────────
    def reload(self):
        self._memory = _load_memory_safe()
        self._rebuild_sections()
        self._update_status()

    def _rebuild_sections(self):
        # Temizle
        for sec in self._sections.values():
            sec.setParent(None)
            sec.deleteLater()
        self._sections.clear()

        # Default kategori sırası — varsa
        priority = [
            "identity", "family", "education", "projects",
            "publications", "technical_expertise", "preferences",
            "wishes", "relationships", "personal_life",
            "strategic_perspective", "character_traits", "notes",
        ]
        existing = list(self._memory.keys())
        ordered = [k for k in priority if k in existing] + \
                  [k for k in existing if k not in priority]

        for cat in ordered:
            entries = self._memory.get(cat, {}) or {}
            if not isinstance(entries, dict):
                continue
            expanded = cat in self._DEFAULT_EXPANDED
            sec = CategorySection(cat, entries, expanded=expanded)
            sec.add_requested.connect(self._on_add_entry)
            sec.edit_requested.connect(self._on_edit_entry)
            sec.delete_requested.connect(self._on_delete_entry)
            self._sections[cat] = sec
            self._content_lay.insertWidget(self._content_lay.count() - 1, sec)

    # ─── Search ───────────────────────────────────────────────────────────────
    def _on_search_changed(self, query: str):
        for sec in self._sections.values():
            sec.setVisible(sec.matches_filter(query))
            if query:
                sec.set_expanded(True)

    # ─── Actions ──────────────────────────────────────────────────────────────
    def _on_add_entry(self, category: str):
        key, ok = QInputDialog.getText(
            self, f"Add to '{category}'", "Key (use_snake_case):"
        )
        if not ok or not key.strip():
            return
        key = key.strip().lower().replace(" ", "_")
        value, ok = QInputDialog.getText(
            self, f"Add to '{category}'", f"Value for '{key}':"
        )
        if not ok or not value.strip():
            return

        self._memory.setdefault(category, {})
        self._memory[category][key] = {
            "value": value.strip(),
            "updated": datetime.now().strftime("%Y-%m-%d"),
        }
        if _save_memory_safe(self._memory):
            self._flash_status(f"✓ Added {category}/{key}")
            self._rebuild_sections()
            # Yeni eklenen kategorinin sectionu varsa aç
            sec = self._sections.get(category)
            if sec:
                sec.set_expanded(True)
        else:
            self._flash_status("✗ Save failed", error=True)

    def _on_edit_entry(self, category: str, key: str, new_value: str):
        if category not in self._memory:
            return
        if key not in self._memory[category]:
            return
        entry = self._memory[category][key]
        if isinstance(entry, dict):
            entry["value"] = new_value
            entry["updated"] = datetime.now().strftime("%Y-%m-%d")
        else:
            self._memory[category][key] = {
                "value": new_value,
                "updated": datetime.now().strftime("%Y-%m-%d"),
            }
        if _save_memory_safe(self._memory):
            self._flash_status(f"✓ Updated {category}/{key}")
            bus.memory_entry_edited.emit(category, key, new_value)
        else:
            self._flash_status("✗ Save failed", error=True)

    def _on_delete_entry(self, category: str, key: str):
        reply = QMessageBox.question(
            self, "Delete entry",
            f"Delete {category}/{key}?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if category in self._memory and key in self._memory[category]:
            del self._memory[category][key]
            if _save_memory_safe(self._memory):
                self._flash_status(f"✓ Deleted {category}/{key}")
                bus.memory_entry_deleted.emit(category, key)
                self._rebuild_sections()
                # Section'ı tekrar aç
                sec = self._sections.get(category)
                if sec:
                    sec.set_expanded(True)
            else:
                self._flash_status("✗ Save failed", error=True)

    def _add_category(self):
        name, ok = QInputDialog.getText(
            self, "New category", "Category name (snake_case):"
        )
        if not ok or not name.strip():
            return
        name = name.strip().lower().replace(" ", "_")
        if name in self._memory:
            self._flash_status(f"Category '{name}' already exists", error=True)
            return
        self._memory[name] = {}
        if _save_memory_safe(self._memory):
            self._flash_status(f"✓ Added category {name}")
            self._rebuild_sections()

    def _reset_all(self):
        reply = QMessageBox.warning(
            self, "Reset all memory",
            "⚠️ This will DELETE ALL memory entries.\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # Double confirm
        reply = QMessageBox.warning(
            self, "Really sure?",
            "Type-confirm: this clears identity, projects, all categories.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._memory = {}
        if _save_memory_safe(self._memory):
            self._flash_status("✓ Memory cleared")
            self._rebuild_sections()

    def _export_json(self):
        if not self._memory:
            self._flash_status("Nothing to export", error=False)
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export memory snapshot",
            f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._memory, f, indent=2, ensure_ascii=False)
            self._flash_status(f"✓ Exported to {Path(path).name}")
        except Exception as e:
            self._flash_status(f"✗ Export failed: {e}", error=True)

    # ─── External event ───────────────────────────────────────────────────────
    def _on_memory_updated_external(self, snapshot: dict):
        """Backend memory'i değiştirdiğinde (örn. save_memory tool call)."""
        self._memory = snapshot or _load_memory_safe()
        self._rebuild_sections()
        self._flash_status("Memory refreshed")

    # ─── Status feedback ──────────────────────────────────────────────────────
    def _update_status(self):
        total = sum(len(v) for v in self._memory.values() if isinstance(v, dict))
        cat_count = len([v for v in self._memory.values() if isinstance(v, dict)])
        self._status_lbl.setText(f"{total} entries in {cat_count} categories")

    def _flash_status(self, msg: str, error: bool = False):
        th = get_theme()
        color = th.palette.warning if error else th.palette.success
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color: {color}; background: transparent; padding: 2px 0; "
            f"font-family: '{th.typography.mono_family}'; "
            f"font-size: {th.typography.size_xs}pt;"
        )
        # 2 saniye sonra normale dön
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2200, self._update_status_styled)

    def _update_status_styled(self):
        self._update_status()
        th = get_theme()
        self._status_lbl.setStyleSheet(
            f"color: {th.palette.text_dim}; background: transparent; padding: 2px 0; "
            f"font-family: '{th.typography.mono_family}'; "
            f"font-size: {th.typography.size_xs}pt;"
        )

    # ─── Theming ──────────────────────────────────────────────────────────────
    def _apply_theme(self, theme: Theme):
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        self._search_input.setFont(QFont(t.mono_family, t.size_sm))
        self._search_input.setStyleSheet(f"""
            #MemorySearch {{
                background: {p.dark};
                color: {p.text_strong};
                border: 1px solid {p.border};
                border-radius: {s.radius_sm}px;
                padding: 4px {s.md}px;
                min-height: 22px;
            }}
            #MemorySearch:focus {{ border: 1px solid {p.secondary}; }}
        """)

        self._update_status_styled()

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


__all__ = ["MemoryInspectorView", "CategorySection", "EntryRow"]
