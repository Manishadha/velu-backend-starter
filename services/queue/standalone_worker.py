# services/queue/standalone_worker.py
from __future__ import annotations

from services.queue.worker_entry import worker_main


def main() -> None:
    """
    CLI / module entrypoint.

    Delegates to the same worker_main that tests import from
    services.queue.worker_entry, so there is only ONE worker
    implementation in the whole codebase.
    """
    worker_main()


if __name__ == "__main__":
    main()
