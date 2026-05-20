"""
SidebarMetrics — sol panel.

İçerik:
  ◈ CONSTRUCT MONITOR
  [CPU bar]
  [MEM bar]
  [NET bar]
  [GPU bar]
  [TMP bar]
  ────
  Info panel:
    UP   12:34
    PROC  342
    OS   WINDOWS
  ────
  [Status pills:]
    MIND CORE ONLINE
    ZION LINK OPEN
    PROTOCOL NEBUCHADNEZZAR
"""
from __future__ import annotations

import platform
import time

import psutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..components import MetricBar, Panel, SectionHeader, StatusPill
from ..state import bus, metrics
from ..themes import Theme, get_theme


_OS = platform.system()


class SidebarMetrics(QWidget):
    """
    Sol panel: sistem metrikleri + statü etiketleri.
    SysMetrics singleton'undan 2 saniyede bir snapshot okur.
    Tema değişimini otomatik yakalar (komponentler kendi başına).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")

        th = get_theme()
        self.setFixedWidth(th.spacing.sidebar_w)

        self._build_ui(th)

        bus.theme_changed.connect(self._on_theme)
        self._apply_container_style(th)

        # 2 saniyede bir metric güncelle
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._refresh)
        self._tmr.start(2000)
        # İlk frame
        QTimer.singleShot(50, self._refresh)

    # ─── UI build ─────────────────────────────────────────────────────────────
    def _build_ui(self, theme: Theme) -> None:
        s = theme.spacing
        lay = QVBoxLayout(self)
        lay.setContentsMargins(s.lg, s.lg, s.lg, s.lg)
        lay.setSpacing(s.md)

        # ─── Section: monitor ─────────────────────────────────────────────────
        lay.addWidget(SectionHeader("CONSTRUCT MONITOR"))

        # Metric bars — tone'lar:
        #   CPU = secondary (mavi)
        #   MEM = secondary tonunda ama biraz farklı
        #   NET = primary (yeşil "transmission")
        #   GPU = secondary
        #   TMP = accent (sıcaklık → kırmızı tonu)
        self._bar_cpu = MetricBar("CPU", tone="secondary")
        self._bar_mem = MetricBar("MEM", tone="secondary")
        self._bar_net = MetricBar("NET", tone="primary")
        self._bar_gpu = MetricBar("GPU", tone="secondary")
        self._bar_tmp = MetricBar("TMP", tone="accent")

        for bar in (self._bar_cpu, self._bar_mem, self._bar_net,
                    self._bar_gpu, self._bar_tmp):
            lay.addWidget(bar)

        # ─── Info panel: UP/PROC/OS ───────────────────────────────────────────
        self._info_panel = Panel()
        self._uptime_lbl = self._info_label("UP  --:--", tone="primary")
        self._proc_lbl   = self._info_label("PROC  --",  tone="text_medium")
        os_name = {"Windows": "WIN", "Darwin": "macOS", "Linux": "LINUX"}.get(_OS, _OS.upper())
        self._os_lbl     = self._info_label(f"OS  {os_name}", tone="secondary")

        self._info_panel.add_widget(self._uptime_lbl)
        self._info_panel.add_widget(self._proc_lbl)
        self._info_panel.add_widget(self._os_lbl)
        lay.addWidget(self._info_panel)

        # ─── Status pills ─────────────────────────────────────────────────────
        # Tema karakterine uygun — ileride tema-bazlı string'lere çevirebiliriz
        pills_data = self._pills_for(theme)
        self._pills = []
        for txt, tone in pills_data:
            pill = StatusPill(txt, tone=tone)
            self._pills.append(pill)
            lay.addWidget(pill)

        lay.addStretch()

    def _info_label(self, text: str, tone: str = "text_medium") -> QLabel:
        """Info panel için renkli mini etiket."""
        th = get_theme()
        t = th.typography
        lbl = QLabel(text)
        lbl.setProperty("tone", tone)
        lbl.setFont(QFont(t.mono_family, t.size_sm, QFont.Weight.Bold))
        self._restyle_info_label(lbl, th)
        return lbl

    def _restyle_info_label(self, lbl: QLabel, theme: Theme) -> None:
        tone = lbl.property("tone") or "text_medium"
        color = getattr(theme.palette, tone, theme.palette.text_medium)
        lbl.setStyleSheet(
            f"color: {color}; background: transparent; border: none;"
        )

    def _pills_for(self, theme: Theme) -> list[tuple[str, str]]:
        """Tema karakterine göre alt köşedeki statü etiketleri."""
        if theme.slug == "morpheus":
            return [
                ("MIND CORE\nONLINE",         "primary"),
                ("ZION\nLINK OPEN",           "secondary"),
                ("PROTOCOL\nNEBUCHADNEZZAR",  "text_dim"),
            ]
        if theme.slug == "mission_control":
            return [
                ("FLIGHT\nNOMINAL",           "primary"),
                ("TELEMETRY\nLOCKED",         "secondary"),
                ("MISSION\nMARK XXXIX",       "text_dim"),
            ]
        # minimal / default
        return [
            ("Status\nOnline",      "primary"),
            ("Network\nConnected",  "secondary"),
            ("Version\n39.1.0",     "text_dim"),
        ]

    # ─── Refresh loop ─────────────────────────────────────────────────────────
    def _refresh(self) -> None:
        snap = metrics.snapshot()

        # CPU
        cpu = snap["cpu"]
        self._bar_cpu.set_value(cpu, f"{cpu:.0f}%")

        # MEM
        mem = snap["mem"]
        self._bar_mem.set_value(mem, f"{mem:.0f}%")

        # NET — MB/s, küçükse KB/s gösteri
        net = snap["net"]
        if net < 1.0:
            net_str = f"{net * 1024:.0f}KB/s"
        else:
            net_str = f"{net:.1f}MB/s"
        net_pct = min(100, net * 10)
        self._bar_net.set_value(net_pct, net_str)

        # GPU
        gpu = snap["gpu"]
        if gpu >= 0:
            self._bar_gpu.set_value(gpu, f"{gpu:.0f}%")
        else:
            self._bar_gpu.set_value(0, "N/A")

        # TMP
        tmp = snap["tmp"]
        if tmp >= 0:
            tmp_pct = min(100, tmp)  # ° direkt yüzde olarak (100°C = full)
            self._bar_tmp.set_value(tmp_pct, f"{tmp:.0f}°C")
        else:
            self._bar_tmp.set_value(0, "N/A")

        # Uptime
        try:
            elapsed = time.time() - psutil.boot_time()
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
        except Exception:
            self._uptime_lbl.setText("UP  --:--")

        # Process count
        try:
            self._proc_lbl.setText(f"PROC  {len(psutil.pids())}")
        except Exception:
            self._proc_lbl.setText("PROC  --")

    # ─── Theming ──────────────────────────────────────────────────────────────
    def _on_theme(self, theme: Theme) -> None:
        # Sidebar genişliği tema spacing'inden — tema değişiminde yenile
        self.setFixedWidth(theme.spacing.sidebar_w)
        self._apply_container_style(theme)

        # Info label'ları yeniden renklendir
        for lbl in (self._uptime_lbl, self._proc_lbl, self._os_lbl):
            self._restyle_info_label(lbl, theme)

        # Pills'i yeniden inşa et (tema karakteri farklıysa text de değişir)
        new_pills_data = self._pills_for(theme)
        for pill, (txt, tone) in zip(self._pills, new_pills_data):
            pill.set_text(txt)
            pill.set_tone(tone)

    def _apply_container_style(self, theme: Theme) -> None:
        p = theme.palette
        self.setStyleSheet(f"""
            #Sidebar {{
                background: {p.dark};
                border-right: 1px solid {p.border};
            }}
        """)


__all__ = ["SidebarMetrics"]
