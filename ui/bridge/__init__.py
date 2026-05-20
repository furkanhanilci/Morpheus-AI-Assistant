"""
ui.bridge — Backend → UI bus köprüsü.

Backend kodu (agent/executor.py, main.py vs.) buradaki yardımcıları kullanarak
UI'a event gönderir. UI bunlardan habersiz olarak çalışmaya devam eder; bridge
sadece backend'e seçenek sunar.

Backend tek satırla emit eder:
    from ui.bridge import emit_tool_started
    emit_tool_started("web_search", {"query": q})
"""
from .executor_bridge import (
    emit_plan_started, emit_plan_step, emit_plan_finished,
    emit_tool_started, emit_tool_finished,
    tool_call, ExecutorReporter,
)

__all__ = [
    "emit_plan_started", "emit_plan_step", "emit_plan_finished",
    "emit_tool_started", "emit_tool_finished",
    "tool_call", "ExecutorReporter",
]
