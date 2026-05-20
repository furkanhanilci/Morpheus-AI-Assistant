"""
MainWindow shell — Final (PR-8).

Yapı:
  Header (title + state)
  ├── Sidebar (SidebarMetrics)
  ├── Center (HudCanvas + InputBar)
  └── RightDock (TabBar + tabbed views)
  Footer

Keyboard:
  F4    → mute toggle
  F11   → fullscreen toggle
  SPACE → PTT (sadece listening_mode = PTT iken)

Auto-throttle:
  App background → PerfLevel.LOW (otomatik)
  App foreground → previous level (otomatik restore)
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeyEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow,
    QSizePolicy, QVBoxLayout, QWidget,
)

from .components import DropZone, InputBar, Panel, SectionHeader, ToggleButton
from .overlays import SetupOverlay
from .state import bus, state, ConnState, ListeningMode
from .themes import PerfLevel, Theme, get_theme
from .views import HudCanvas, RightDock, SidebarMetrics


_DEFAULT_W, _DEFAULT_H = 1180, 760
_MIN_W,     _MIN_H     = 880, 600


class MainWindow(QMainWindow):
    """
    Mimari:
        ┌─────────────────────────────────────────────┐
        │  Header (title + state)                     │
        ├─────────┬──────────────────────┬────────────┤
        │ Sidebar │     HUD area         │ Right dock │
        │ (real)  │  (placeholder PR-3)  │ (PR-4 tab) │
        │         │                      │            │
        │         │   [InputBar]         │            │
        ├─────────┴──────────────────────┴────────────┤
        │  Footer                                     │
        └─────────────────────────────────────────────┘
    """

    def __init__(self, face_path: str = ""):
        super().__init__()
        self._face_path = face_path
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)
        self._center_on_screen()

        self._build_ui()
        self._wire_signals()
        self._wire_shortcuts()

        # Lazy — wait_for_api_key() çağrıldığında oluşturulur
        self._setup_overlay: SetupOverlay | None = None

        self._apply_theme(get_theme())

    def show_setup_blocking(self) -> None:
        """API key onboarding modal'ını göster ve key girilene kadar blokla."""
        if self._setup_overlay is None:
            self._setup_overlay = SetupOverlay(self)
        self._setup_overlay.wait_for_key()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = self._build_header()
        root.addWidget(self._header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Sol: gerçek sidebar
        self._sidebar = SidebarMetrics()
        body.addWidget(self._sidebar, stretch=0)

        # Orta: HUD area + InputBar (alt)
        center = QWidget()
        center.setObjectName("CenterColumn")
        center_lay = QVBoxLayout(center)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(0)

        self._hud_area = self._build_hud_placeholder()
        center_lay.addWidget(self._hud_area, stretch=1)

        self._input_wrap = self._build_input_area()
        center_lay.addWidget(self._input_wrap)

        body.addWidget(center, stretch=5)

        # Sağ: tab placeholder
        self._right_dock = self._build_right_dock_placeholder()
        body.addWidget(self._right_dock, stretch=0)

        body_wrap = QWidget()
        body_wrap.setLayout(body)
        root.addWidget(body_wrap, stretch=1)

        self._footer = self._build_footer()
        root.addWidget(self._footer)

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setObjectName("Header")
        th = get_theme()
        w.setFixedHeight(th.spacing.header_h)

        lay = QHBoxLayout(w)
        lay.setContentsMargins(th.spacing.xl, 0, th.spacing.xl, 0)

        self._title_lbl = QLabel(th.welcome_banner)
        self._title_lbl.setObjectName("HeaderTitle")
        lay.addWidget(self._title_lbl)
        lay.addStretch()

        self._status_lbl = QLabel("●  " + th.label_jacking_in)
        self._status_lbl.setObjectName("HeaderStatus")
        lay.addWidget(self._status_lbl)

        return w

    def _build_hud_placeholder(self) -> QWidget:
        # PR-3: gerçek HudCanvas — animasyonlu compositor.
        self._hud = HudCanvas(self._face_path)
        self._hud.setObjectName("HudArea")
        return self._hud

    def _refresh_hud_placeholder(self) -> None:
        # HudCanvas tema değişimini kendi içinde halleder, burada bir şey yapmaya gerek yok.
        pass

    def _build_input_area(self) -> QWidget:
        th = get_theme()
        wrap = QWidget()
        wrap.setObjectName("InputArea")

        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(th.spacing.xxl, th.spacing.md,
                               th.spacing.xxl, th.spacing.lg)
        lay.setSpacing(th.spacing.sm)

        self._input_bar = InputBar()
        lay.addWidget(self._input_bar)

        return wrap

    def _build_right_dock_placeholder(self) -> QWidget:
        """
        PR-4: gerçek RightDock — tab sistemi (Chat / Plan / Tools / Memory / Files / Settings).
        Eski drop_zone ve mute/fullscreen butonları artık ilgili tab içinde
        (Files ve Settings) ya da global olarak header'da yer alıyor.
        """
        self._right_dock = RightDock()

        # mute toggle artık bir external buton değil; sadece state üzerinden yönetilir.
        # Backwards compat için file_count_lbl ve _mute_btn referanslarını dummy widget yap:
        self._file_count_lbl = QLabel()
        self._mute_btn = None
        self._fullscreen_btn = None

        return self._right_dock

    def _build_footer(self) -> QWidget:
        th = get_theme()
        w = QWidget()
        w.setObjectName("Footer")
        w.setFixedHeight(th.spacing.footer_h)

        lay = QHBoxLayout(w)
        lay.setContentsMargins(th.spacing.xl, 0, th.spacing.xl, 0)

        self._shortcuts_lbl = QLabel(
            "[F4] Mute  ·  [F11] Fullscreen  ·  [SPACE] PTT"
        )
        self._shortcuts_lbl.setObjectName("FooterShortcuts")
        lay.addWidget(self._shortcuts_lbl)

        lay.addStretch()

        self._brand_lbl = QLabel("Furkan Hanilçi © 2026")
        self._brand_lbl.setObjectName("FooterBrand")
        lay.addWidget(self._brand_lbl)

        return w

    # ─── Signals ──────────────────────────────────────────────────────────────
    def _wire_signals(self) -> None:
        bus.theme_changed.connect(self._on_theme_changed)
        bus.state_changed.connect(self._on_state_changed)
        bus.mute_set.connect(self._on_mute_set)
        bus.file_added.connect(self._on_file_added)
        bus.file_removed.connect(self._on_file_removed)
        bus.files_cleared.connect(self._on_files_cleared)

    def _wire_shortcuts(self) -> None:
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)

        # Application focus listener — pencere arka plana geçince
        # otomatik LOW perf moduna, dönünce orijinal seviyeye.
        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_app_state_changed)

        # Auto-throttle: pencere foreground'a dönünce restore edilecek seviye
        self._saved_perf_level: PerfLevel | None = None

    def _toggle_fullscreen(self) -> None:
        was_full = self.isFullScreen()
        if was_full:
            self.showNormal()
        else:
            self.showFullScreen()
        # _fullscreen_btn artık None — null-safe
        if self._fullscreen_btn is not None:
            self._fullscreen_btn.set_checked(not was_full)

    def _toggle_mute(self) -> None:
        state.set_muted(not state.muted)

    # ─── PTT (push-to-talk) ───────────────────────────────────────────────────
    def keyPressEvent(self, ev: QKeyEvent) -> None:
        # SPACE basılı tutuldukça PTT aktif — sadece listening_mode = PTT iken
        if (ev.key() == Qt.Key.Key_Space
                and not ev.isAutoRepeat()
                and state.listening_mode == ListeningMode.PTT):
            state.set_ptt_active(True)
            ev.accept()
            return
        super().keyPressEvent(ev)

    def keyReleaseEvent(self, ev: QKeyEvent) -> None:
        if (ev.key() == Qt.Key.Key_Space
                and not ev.isAutoRepeat()
                and state.listening_mode == ListeningMode.PTT):
            state.set_ptt_active(False)
            ev.accept()
            return
        super().keyReleaseEvent(ev)

    # ─── Auto-throttle when window goes background ────────────────────────────
    def _on_app_state_changed(self, app_state) -> None:
        """
        Pencere arka plana / sürgülenince animasyon yükünü düşür.
        Foreground'a dönünce orijinal seviyeye geri al.
        """
        from PyQt6.QtCore import Qt
        if app_state in (Qt.ApplicationState.ApplicationInactive,
                         Qt.ApplicationState.ApplicationHidden,
                         Qt.ApplicationState.ApplicationSuspended):
            # Save current → switch to LOW
            if state.perf_level not in (PerfLevel.LOW, PerfLevel.OFF):
                self._saved_perf_level = state.perf_level
                state.set_perf_level(PerfLevel.LOW)
        elif app_state == Qt.ApplicationState.ApplicationActive:
            # Restore previous level
            if self._saved_perf_level is not None:
                state.set_perf_level(self._saved_perf_level)
                self._saved_perf_level = None

    # ─── Theme handlers ───────────────────────────────────────────────────────
    def _on_theme_changed(self, theme: Theme) -> None:
        self._apply_theme(theme)

    def _on_state_changed(self, state_value: str) -> None:
        th = get_theme()
        p = th.palette
        t = th.typography

        # State → label + color mapping
        label_map = {
            ConnState.LISTENING.value:  (th.label_listening,  p.success),
            ConnState.SPEAKING.value:   (th.label_speaking,   p.primary),
            ConnState.THINKING.value:   (th.label_thinking,   p.secondary),
            ConnState.PROCESSING.value: (th.label_processing, p.secondary),
            ConnState.JACKING_IN.value: (th.label_jacking_in, p.secondary),
            ConnState.MUTED.value:      (th.label_muted,      p.warning),
        }
        label, color = label_map.get(state_value, (state_value, p.text_dim))
        self._status_lbl.setText(f"●  {label}")
        self._status_lbl.setStyleSheet(
            f"color: {color}; "
            f"font-family: '{t.mono_family}', '{t.mono_fallback}'; "
            f"font-size: {t.size_sm}pt; "
            f"background: transparent;"
        )

    def _on_mute_set(self, muted: bool) -> None:
        # PR-4: _mute_btn artık external değil; sadece state üzerinden yönetilir.
        # Settings tab içinde tek bir mute toggle olabilir ileride.
        pass

    def _on_fullscreen_toggle(self, on: bool) -> None:
        if on and not self.isFullScreen():
            self.showFullScreen()
        elif not on and self.isFullScreen():
            self.showNormal()

    # ─── File handlers ────────────────────────────────────────────────────────
    def _on_files_dropped(self, paths: list) -> None:
        for p in paths:
            bus.log_appended.emit(f"FILE: loaded → {p}")

    def _on_file_added(self, _path: str) -> None:
        self._refresh_file_count()

    def _on_file_removed(self, _path: str) -> None:
        self._refresh_file_count()

    def _on_files_cleared(self) -> None:
        self._refresh_file_count()

    def _refresh_file_count(self) -> None:
        # PR-4: file count label artık right dock'ta yok; gelecekte Files tab
        # bunu kendi içinde gösterir.
        pass

    # ─── Theme application ────────────────────────────────────────────────────
    def _apply_theme(self, theme: Theme) -> None:
        p = theme.palette
        t = theme.typography
        s = theme.spacing

        self.setWindowTitle(theme.welcome_banner or theme.name)

        self.setStyleSheet(f"""
            QMainWindow {{ background: {p.bg}; }}

            #Header {{
                background: {p.dark};
                border-bottom: 1px solid {p.border};
            }}
            #HeaderTitle {{
                color: {p.primary};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_md}pt;
                font-weight: bold;
            }}
            #HeaderStatus {{
                color: {p.secondary};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_sm}pt;
            }}

            #CenterColumn {{ background: {p.bg}; }}
            #HudArea {{ background: {p.bg}; }}
            #HudPlaceholder {{
                color: {p.text_dim};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_md}pt;
            }}

            #InputArea {{
                background: {p.bg};
                border-top: 1px solid {p.border_dim};
            }}

            #RightDock {{
                background: {p.dark};
                border-left: 1px solid {p.border};
            }}
            #FileCountLabel {{
                color: {p.text_dim};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
                background: transparent;
                padding: {s.xs}px 0;
            }}
            #Placeholder {{
                color: {p.text_dim};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
                background: transparent;
                padding: {s.md}px 0;
            }}

            #Footer {{
                background: {p.dark};
                border-top: 1px solid {p.border};
            }}
            #FooterShortcuts {{
                color: {p.text_dim};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
            }}
            #FooterBrand {{
                color: {p.secondary_dim};
                font-family: "{t.mono_family}", "{t.mono_fallback}";
                font-size: {t.size_xs}pt;
            }}
        """)

        self._title_lbl.setText(theme.welcome_banner or theme.name)
        self._refresh_hud_placeholder()
        self._on_state_changed(state.conn_state.value)
