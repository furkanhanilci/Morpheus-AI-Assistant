"""
SysMetrics — sistem metrikleri toplayıcı.

Background thread'de psutil ve OS-spesifik komutlarla periyodik olarak
CPU/MEM/NET/GPU/Temperature okur. snapshot() ile thread-safe okuma sağlar.

Eski ui.py'deki `_SysMetrics` class'ının taşınmış, temizlenmiş hali.
"""
from __future__ import annotations

import platform
import re
import subprocess
import threading
import time

import psutil

_OS = platform.system()


class SysMetrics:
    """Singleton background metric collector."""

    def __init__(self, interval_s: float = 1.5):
        self.cpu  = 0.0
        self.mem  = 0.0
        self.net  = 0.0    # MB/s
        self.gpu  = -1.0   # % (negative = unavailable)
        self.tmp  = -1.0   # °C (negative = unavailable)

        self._lock = threading.Lock()
        self._interval_s = interval_s
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True, name="SysMetrics")
        t.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                self._update()
            except Exception:
                # Hata patlamasın — bir tur atla
                pass
            time.sleep(self._interval_s)

    def _update(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent

        nc  = psutil.net_io_counters()
        now = time.time()
        dt  = now - self._last_net_t
        if dt > 0:
            sent = (nc.bytes_sent - self._last_net.bytes_sent) / dt
            recv = (nc.bytes_recv - self._last_net.bytes_recv) / dt
            net  = (sent + recv) / (1024 * 1024)
        else:
            net = 0.0
        self._last_net   = nc
        self._last_net_t = now

        gpu = self._get_gpu()
        tmp = self._get_temp()

        with self._lock:
            self.cpu = cpu
            self.mem = mem
            self.net = net
            self.gpu = gpu
            self.tmp = tmp

    # ─── GPU ──────────────────────────────────────────────────────────────────
    def _get_gpu(self) -> float:
        # NVIDIA
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2,
            )
            if r.returncode == 0:
                vals = [float(v.strip()) for v in r.stdout.strip().split("\n") if v.strip()]
                if vals:
                    return sum(vals) / len(vals)
        except Exception:
            pass

        # Linux: AMD ROCm or Intel
        if _OS == "Linux":
            try:
                r = subprocess.run(
                    ["rocm-smi", "--showuse", "--csv"],
                    capture_output=True, text=True, timeout=2,
                )
                if r.returncode == 0:
                    for line in r.stdout.strip().split("\n"):
                        parts = line.split(",")
                        if len(parts) >= 2:
                            try:
                                return float(parts[1].strip().replace("%", ""))
                            except ValueError:
                                pass
            except Exception:
                pass

            try:
                r = subprocess.run(
                    ["intel_gpu_top", "-J", "-s", "500"],
                    capture_output=True, text=True, timeout=1,
                )
                if r.returncode == 0 and "Render/3D" in r.stdout:
                    m = re.search(r'"busy":\s*([\d.]+)', r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        # macOS
        if _OS == "Darwin":
            try:
                r = subprocess.run(
                    ["sudo", "-n", "powermetrics", "-n", "1", "-i", "500",
                     "--samplers", "gpu_power"],
                    capture_output=True, text=True, timeout=2,
                )
                if r.returncode == 0 and "GPU" in r.stdout:
                    m = re.search(r'GPU\s+Active:\s+([\d.]+)%', r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        return -1.0

    # ─── Temperature ──────────────────────────────────────────────────────────
    def _get_temp(self) -> float:
        # psutil sensors_temperatures (Linux + bazı platformlar)
        try:
            temps = psutil.sensors_temperatures()
            candidates = [
                "coretemp", "k10temp", "cpu_thermal", "acpitz",
                "cpu-thermal", "zenpower", "it8688",
            ]
            for name in candidates:
                if name in temps:
                    entries = temps[name]
                    if entries:
                        return entries[0].current
            for entries in temps.values():
                if entries:
                    return entries[0].current
        except Exception:
            pass

        # macOS — osx-cpu-temp
        if _OS == "Darwin":
            try:
                r = subprocess.run(
                    ["osx-cpu-temp"],
                    capture_output=True, text=True, timeout=2,
                )
                if r.returncode == 0:
                    m = re.search(r"([\d.]+)", r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        # Windows — WMI thermal zone
        if _OS == "Windows":
            try:
                r = subprocess.run(
                    [
                        "powershell", "-Command",
                        "(Get-WmiObject MSAcpi_ThermalZoneTemperature "
                        "-Namespace root/wmi).CurrentTemperature",
                    ],
                    capture_output=True, text=True, timeout=3,
                )
                if r.returncode == 0 and r.stdout.strip():
                    raw = float(r.stdout.strip().split("\n")[0])
                    return (raw / 10.0) - 273.15
            except Exception:
                pass

        return -1.0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu": self.cpu,
                "mem": self.mem,
                "net": self.net,
                "gpu": self.gpu,
                "tmp": self.tmp,
            }


# Singleton — modül ilk import'ta otomatik start eder
metrics = SysMetrics()
metrics.start()


__all__ = ["SysMetrics", "metrics"]
