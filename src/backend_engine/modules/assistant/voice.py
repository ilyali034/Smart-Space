

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

RecognizerFactory = Callable[[Any, int, "str | None"], Any]
StreamFactory = Callable[[int, int, Callable[..., None]], Any]


def _default_recognizer(model: Any, samplerate: int, grammar: str | None) -> Any:
    from vosk import KaldiRecognizer

    return KaldiRecognizer(model, samplerate, grammar) if grammar else KaldiRecognizer(model, samplerate)


def _default_stream(samplerate: int, blocksize: int, callback: Callable[..., None]) -> Any:
    import sounddevice as sd

    return sd.RawInputStream(
        samplerate=samplerate, blocksize=blocksize, dtype="int16", channels=1, callback=callback
    )


class VoiceRecognizer:
    def __init__(
        self,
        model_path: str | Path,
        samplerate: int = 16000,
        blocksize: int = 4000,  # 0.25 s per chunk at 16 kHz
        *,
        model: Any = None,
        recognizer_factory: RecognizerFactory = _default_recognizer,
        stream_factory: StreamFactory = _default_stream,
    ) -> None:
        self._model_path = Path(model_path)
        self._model = model
        self.samplerate = samplerate
        self._blocksize = blocksize
        self._make_recognizer = recognizer_factory
        self._make_stream = stream_factory
        # bounded: ~12 s of audio. If the consumer stalls we drop audio instead of eating memory.
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=50)
        self._loop: asyncio.AbstractEventLoop | None = None

    # ---- plumbing ----

    def _get_model(self) -> Any:
        if self._model is None:  # load once; this is slow (seconds) and uses a lot of RAM
            if not self._model_path.exists():  # check first: a clear error beats an obscure Vosk crash
                raise FileNotFoundError(f"Vosk model not found: {self._model_path}")
            from vosk import Model

            self._model = Model(str(self._model_path))
        return self._model

    def _on_audio(self, indata: Any, _frames: int, _time: Any, status: Any) -> None:
        """Called by PortAudio on its own thread: only hand the bytes to the event loop."""
        if status:
            log.warning("audio status: %s", status)
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self._push, bytes(indata))

    def _push(self, data: bytes) -> None:
        try:
            self._queue.put_nowait(data)
        except asyncio.QueueFull:
            log.warning("audio queue full, dropping a chunk")

    def flush(self) -> None:
        """Drop buffered audio. Call it after TTS so the assistant does not hear itself."""
        while not self._queue.empty():
            self._queue.get_nowait()

    @asynccontextmanager
    async def _listening(self) -> AsyncIterator[None]:
        self._loop = asyncio.get_running_loop()
        self.flush()  # stale audio (e.g. the wake word itself) must not leak into the next recognition
        with self._make_stream(self.samplerate, self._blocksize, self._on_audio):
            try:
                yield
            finally:
                self._loop = None
        self.flush()

    # ---- public API ----

    async def wait_for_wake_word(
        self, word: str, *, timeout: float | None = None, use_grammar: bool = True
    ) -> bool:
        """True when `word` was heard, False on timeout.

        Matches whole words only ("алекс" does not match "алексей") and also reacts to partial
        results, so it fires while you are still speaking instead of after a pause.
        use_grammar restricts recognition to [word, unknown] - faster and more accurate; it works
        with Vosk small models, set it to False for large (static graph) models."""
        target = word.lower().strip()
        grammar = json.dumps([target, "[unk]"], ensure_ascii=False) if use_grammar else None
        rec = self._make_recognizer(self._get_model(), self.samplerate, grammar)
        needle = f" {target} "

        async def listen() -> bool:
            while True:
                data = await self._queue.get()
                if rec.AcceptWaveform(data):
                    text = json.loads(rec.Result()).get("text", "")
                else:
                    text = json.loads(rec.PartialResult()).get("partial", "")
                if needle in f" {text.lower()} ":
                    return True

        async with self._listening():
            try:
                return await asyncio.wait_for(listen(), timeout)
            except asyncio.TimeoutError:
                return False

    async def recognize_phrase(
        self, *, timeout: float = 10.0, on_partial: Callable[[str], None] | None = None
    ) -> str:
        """Return the first complete non-empty phrase.

        A phrase is complete when Vosk detects the end of speech (a pause). On timeout the last
        partial text is returned (it may be an unfinished phrase), or "" if nothing was said.
        on_partial(text) is called with live text, e.g. to show it in a UI."""
        rec = self._make_recognizer(self._get_model(), self.samplerate, None)
        last_partial = ""

        async def listen() -> str:
            nonlocal last_partial
            while True:
                data = await self._queue.get()
                if rec.AcceptWaveform(data):
                    text = json.loads(rec.Result()).get("text", "").strip()
                    if text:
                        return text
                else:
                    partial = json.loads(rec.PartialResult()).get("partial", "").strip()
                    if partial and partial != last_partial:
                        last_partial = partial
                        if on_partial:
                            on_partial(partial)

        async with self._listening():
            try:
                return await asyncio.wait_for(listen(), timeout)
            except asyncio.TimeoutError:
                return last_partial