"""
Executor → UI bus köprüsü.

Backend (agent/executor.py) iki seçenekle entegre olabilir:

Seçenek A — minimal invaziv (önerilen):
    from ui.bridge import emit_plan_started, emit_plan_step, emit_plan_finished

    emit_plan_started(goal, steps)
    for step in steps:
        emit_plan_step(step_num, tool, "running")
        # ...
        emit_plan_step(step_num, tool, "ok", duration_s=2.1, result="...")
    emit_plan_finished(success=True, summary="...")

Seçenek B — wrapper class:
    from ui.bridge import ExecutorReporter

    reporter = ExecutorReporter()
    reporter.plan_started(goal, steps)
    reporter.step_done(step_num, "ok", duration_s=2.1)

Iki API'de aynı bus signal'larını emit eder. Backend bağlı değilse import bile
edilmez — bu modül backend'i hiçbir şekilde değiştirmez, sadece signal göndermek
isteyen yere "şu fonksiyonu çağır" diyor.

Aynı şey tool çağrıları için: emit_tool_started / emit_tool_finished
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Optional

from ..state import bus


# ─── Plan signals ─────────────────────────────────────────────────────────────
def emit_plan_started(goal: str, steps: list[dict]) -> None:
    """
    Plan başladığını UI'a bildir.
    steps formatı: [{"step": 1, "tool": "web_search", "description": "..."}, ...]
    """
    payload = {"goal": goal, "steps": steps}
    bus.plan_started.emit(payload)


def emit_plan_step(
    step_num: int,
    tool: str,
    status: str,                      # "running" | "ok" | "err" | "pending" | "skip"
    duration_s: float = 0.0,
    result: str = "",
    description: str = "",
    error: str = "",
) -> None:
    """Plan'ın bir adımı hakkında durum güncellemesi."""
    payload = {
        "step":        step_num,
        "tool":        tool,
        "status":      status,
        "duration_s":  duration_s,
        "result":      result,
        "description": description,
        "error":       error,
    }
    bus.plan_step.emit(payload)


def emit_plan_finished(success: bool, summary: str = "") -> None:
    bus.plan_finished.emit({"success": success, "summary": summary})


# ─── Tool signals ─────────────────────────────────────────────────────────────
def emit_tool_started(tool_name: str, params: dict | None = None) -> None:
    bus.tool_started.emit(tool_name, params or {})


def emit_tool_finished(
    tool_name: str,
    ok: bool = True,
    duration_s: float = 0.0,
    result: Any = "",
    error: str = "",
) -> None:
    bus.tool_finished.emit(tool_name, {
        "ok":         ok,
        "duration_s": duration_s,
        "result":     str(result)[:500],   # uzun string'leri kes
        "error":      error,
    })


@contextmanager
def tool_call(tool_name: str, params: dict | None = None):
    """
    Bir tool çağrısını otomatik olarak start/finish event'leriyle wrap'ler.

    Kullanım:
        with tool_call("web_search", params={"query": "..."}) as report:
            result = do_search(...)
            report.set_result(result)
    """
    class _Report:
        def __init__(self):
            self.result = ""
            self.error = ""
            self.ok = True

        def set_result(self, r):
            self.result = r

        def set_error(self, e):
            self.error = str(e)
            self.ok = False

    r = _Report()
    t0 = time.time()
    emit_tool_started(tool_name, params)
    try:
        yield r
    except Exception as e:
        r.set_error(e)
        raise
    finally:
        duration = time.time() - t0
        emit_tool_finished(
            tool_name,
            ok=r.ok,
            duration_s=duration,
            result=r.result,
            error=r.error,
        )


class ExecutorReporter:
    """
    AgentExecutor için OOP wrapper. Backend kodu tercih ederse bunu kullanır.
    """

    def __init__(self):
        self._step_starts: dict[int, float] = {}

    def plan_started(self, goal: str, steps: list[dict]) -> None:
        emit_plan_started(goal, steps)

    def step_started(self, step_num: int, tool: str, description: str = "") -> None:
        self._step_starts[step_num] = time.time()
        emit_plan_step(step_num, tool, "running", description=description)

    def step_done(
        self,
        step_num: int,
        tool: str,
        status: str = "ok",          # "ok" | "err" | "skip"
        result: str = "",
        error: str = "",
    ) -> None:
        t0 = self._step_starts.pop(step_num, time.time())
        duration = time.time() - t0
        emit_plan_step(
            step_num, tool, status,
            duration_s=duration,
            result=result, error=error,
        )

    def plan_finished(self, success: bool, summary: str = "") -> None:
        emit_plan_finished(success, summary)


__all__ = [
    "emit_plan_started", "emit_plan_step", "emit_plan_finished",
    "emit_tool_started", "emit_tool_finished",
    "tool_call", "ExecutorReporter",
]
