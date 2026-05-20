# Patch: agent/executor.py — Bridge integration

Bu patch'i `agent/executor.py`'a uygulayarak Plan View + Tool Activity feed'ini
canlı olarak doldurursun. Uygulamazsan UI normal çalışır, sadece o iki view
boş kalır.

## 1) Dosyanın üstüne (import'lardan sonra) ekle:

```python
# ─── UI bridge — backend bağlı değilse no-op ──────────────────────────────────
try:
    from ui.bridge import (
        emit_plan_started, emit_plan_step, emit_plan_finished,
        emit_tool_started, emit_tool_finished,
    )
except ImportError:
    def emit_plan_started(*a, **k): pass
    def emit_plan_step(*a, **k):    pass
    def emit_plan_finished(*a, **k): pass
    def emit_tool_started(*a, **k):  pass
    def emit_tool_finished(*a, **k): pass
```

## 2) `_call_tool()` fonksiyonunun en başına ve return'lerine wrap ekle:

ÖNCE:
```python
def _call_tool(tool: str, parameters: dict, speak: Callable | None) -> Any:
    if tool == "open_app":
        from actions.open_app import open_app
        return open_app(parameters=parameters, ...)
    ...
```

SONRA:
```python
def _call_tool(tool: str, parameters: dict, speak: Callable | None) -> Any:
    import time as _t
    _t0 = _t.time()
    emit_tool_started(tool, parameters or {})
    try:
        result = _dispatch_tool(tool, parameters, speak)
        emit_tool_finished(tool, ok=True, duration_s=_t.time() - _t0,
                           result=str(result)[:300])
        return result
    except Exception as e:
        emit_tool_finished(tool, ok=False, duration_s=_t.time() - _t0,
                           error=str(e))
        raise


def _dispatch_tool(tool: str, parameters: dict, speak: Callable | None) -> Any:
    # ↓ Mevcut _call_tool body'sini buraya taşı (if/elif zinciri olduğu gibi)
    if tool == "open_app":
        from actions.open_app import open_app
        return open_app(parameters=parameters, ...)
    ...
```

## 3) `AgentExecutor.execute()` metoduna emit çağrıları ekle:

`plan = create_plan(goal)` satırından SONRA, while döngüsünden ÖNCE ekle:

```python
emit_plan_started(goal, plan.get("steps", []))
```

`for step in steps:` döngüsü içinde, `print(f"\n[Executor] ▶️ Step {step_num}...")` satırından sonra:

```python
emit_plan_step(step_num, tool, "running", description=desc)
import time as _t; _step_start = _t.time()
```

Step başarıyla bittikten sonra (`step_results[step_num] = result`'tan sonra):

```python
emit_plan_step(step_num, tool, "ok",
               duration_s=_t.time() - _step_start,
               result=str(result)[:300], description=desc)
```

Hata olduğunda (`except Exception as e:` bloğunda, decision verilmeden önce):

```python
emit_plan_step(step_num, tool, "err",
               duration_s=_t.time() - _step_start,
               error=str(e)[:300], description=desc)
```

`return self._summarize(...)` veya `return msg` öncesinde:

```python
emit_plan_finished(True, summary_text)   # success
emit_plan_finished(False, error_text)    # failure
```

## 4) Cancel desteği

`execute()` imzasında zaten `cancel_flag: threading.Event` var.

UI'dan Cancel butonu basıldığında `bus.plan_cancel_requested` emit edilir.
`main.py`'da bunu yakalayıp `cancel_flag.set()` çağırman gerekir:

```python
# main.py içinde, _run_agent_task'i çalıştıran kısımda:
def __init__(self, ...):
    ...
    self._agent_cancel_flag = threading.Event()
    bus.plan_cancel_requested.connect(self._agent_cancel_flag.set)

def _run_agent_task(self, goal):
    self._agent_cancel_flag.clear()
    executor = AgentExecutor()
    return executor.execute(goal, speak=..., cancel_flag=self._agent_cancel_flag)
```

## Test

Patch uygulandıktan sonra herhangi bir agent task çalıştır:
- Plan view doğrudan dolacak ●─── Step 1 [tool] ⟳ → ✓ ile
- Tools tab her tool çağrısını timestamp ile gösterecek
- Cancel butonu plan'ı durduracak (cancel_flag.set sayesinde)

Hiç patch uygulamazsan: UI yine açılır, iki view "No active plan" / "No tool calls"
gösterir. **Patch'in opsiyonel olması garanti.**
