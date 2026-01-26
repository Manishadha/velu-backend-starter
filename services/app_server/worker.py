# services/app_server/worker.py
from __future__ import annotations

import threading
import time
import inspect
from typing import Any

from services.queue.worker_entry import HANDLERS
from services.queue import get_queue

q = get_queue()


class Worker:
    """
    Simple background worker that:
      * pulls jobs from the SQLite queue
      * dispatches them to agent handlers
      * stores results back in the queue

    Note: in "direct-db" mode you usually run `python -m services.queue.worker_entry`.
    This class is for an in-process worker if the API server wants to run jobs itself.
    """

    def __init__(self, poll_interval: float = 0.1) -> None:
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        # Idempotent: if already running, do nothing.
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float | None = 5.0) -> None:
        self._stop_event.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            job_id = q.dequeue()
            if job_id is None:
                time.sleep(self.poll_interval)
                continue

            job = q.load(job_id)
            if not job:
                # job vanished; nothing to do
                continue

            task = str(job.get("task") or "").strip().lower()
            payload: dict[str, Any] = job.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {"raw": payload}

            handler = HANDLERS.get(task)

            if not handler:
                q.fail(job_id, {"error": f"unknown task: {task}"})
                continue

            try:
                # Mirror the flexible dispatch logic from worker_entry._dispatch
                sig = inspect.signature(handler)
                params = list(sig.parameters.values())

                if len(params) == 1:
                    # handle(payload)
                    result = handler(payload)  # type: ignore[arg-type]
                elif len(params) >= 2:
                    # handle(ctx, payload, *rest) -> pass ctx=None
                    result = handler(None, payload)  # type: ignore[misc]
                else:
                    # 0-arg callable
                    result = handler()  # type: ignore[call-arg]

                if not isinstance(result, dict):
                    raise TypeError(f"handler {task!r} returned non-dict result")

                q.finish(job_id, result)
            except Exception as e:
                q.fail(
                    job_id,
                    {
                        "error": f"handler_failed: {type(e).__name__}: {e}",
                        "task": task,
                    },
                )
