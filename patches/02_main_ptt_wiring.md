# Patch: main.py — PTT wiring & bridge integration

## 1) PTT mikrofon kontrolü

`JarvisLive` sınıfının audio listener task'ında (`_listen_audio`) PTT mode
respektine destek ekle.

ÖNCE (mevcut hali, kabaca):
```python
async def _listen_audio(self):
    kwargs = {
        "format":     pyaudio.paInt16,
        "channels":   CHANNELS,
        "rate":       SEND_SAMPLE_RATE,
        "input":      True,
        "frames_per_buffer": CHUNK_SIZE,
    }
    self._audio_stream = await asyncio.to_thread(pya.open, **kwargs)
    while True:
        data = await asyncio.to_thread(
            self._audio_stream.read, CHUNK_SIZE, exception_on_overflow=False
        )
        # Sadece muted değilse veri yolla
        if not self.ui.muted:
            await self._out_queue.put({"data": data, "mime_type": "audio/pcm"})
```

SONRA (PTT-aware):
```python
from ui.state import state, ListeningMode

async def _listen_audio(self):
    kwargs = {
        "format":     pyaudio.paInt16,
        "channels":   CHANNELS,
        "rate":       SEND_SAMPLE_RATE,
        "input":      True,
        "frames_per_buffer": CHUNK_SIZE,
    }
    self._audio_stream = await asyncio.to_thread(pya.open, **kwargs)
    while True:
        data = await asyncio.to_thread(
            self._audio_stream.read, CHUNK_SIZE, exception_on_overflow=False
        )

        # ─── Gate logic ──────────────────────────────────────────
        if self.ui.muted:
            continue                                # muted → no mic
        mode = state.listening_mode
        if mode == ListeningMode.OFF:
            continue                                # text-only → no mic
        if mode == ListeningMode.PTT and not state.ptt_active:
            continue                                # PTT but SPACE not held

        # ─── Send ────────────────────────────────────────────────
        await self._out_queue.put({"data": data, "mime_type": "audio/pcm"})
```

Bu kadar. PTT modunda kullanıcı `SPACE` basılı tutarken `state.ptt_active=True`
olur (MainWindow tarafından zaten yönetiliyor), mic'ten gelen veri Gemini'ye akar.
Bırakınca duruyor.

## 2) Agent cancel desteği (opsiyonel — executor patch'i uygulayanlar için)

`JarvisLive.__init__` içine:

```python
import threading
self._agent_cancel_flag = threading.Event()
bus.plan_cancel_requested.connect(self._agent_cancel_flag.set)
```

`_execute_tool` içinde, `elif name == "agent_task":` branch'inde:

```python
elif name == "agent_task":
    self._agent_cancel_flag.clear()
    from agent.executor import AgentExecutor
    executor = AgentExecutor()
    r = await loop.run_in_executor(
        None,
        lambda: executor.execute(
            args.get("goal", ""),
            speak=self._speak_text,
            cancel_flag=self._agent_cancel_flag,
        )
    )
    result = r or "Done."
```

## 3) Memory inspector ile sync

Memory inspector'a kullanıcı bir entry değiştirdiğinde `bus.memory_entry_edited`
emit edilir. Backend bunu dinlemek isterse:

```python
# JarvisLive.__init__ veya bus listener init noktasında:
bus.memory_entry_edited.connect(self._on_memory_edited_externally)

def _on_memory_edited_externally(self, category: str, key: str, new_value: str):
    # UI'dan değiştirildi — log'la, ya da context'i taze tutmak için bir şey yap
    print(f"[JARVIS] Memory edited via UI: {category}/{key}")
    # Eğer Gemini live session'ında system prompt'a memory dahil ediyorsan,
    # next message'da yenilenecek (otomatik); ekstra bir şey yapma gerekmez.
```

## Test

PTT patch'i uyguladıktan sonra:
1. UI aç, Settings → Input → "PTT (SPACE)" seç
2. SPACE basılı tutarken konuş → Gemini cevap verir
3. SPACE bırakınca mic kesilir, yeni input bekler

Patch uygulamazsan UI'da PTT seçeneği görünür ama her zaman ALWAYS gibi
davranır (UI bus.ptt_pressed emit eder ama backend gate'i yok).
