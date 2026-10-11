"""Background worker entrypoint. Run with: uv run python -m app.worker

Milestone 1 stub: it starts, logs a heartbeat, and stops cleanly on SIGINT/SIGTERM.
The PostgreSQL-backed job queue (ADR-007) is added in Milestone 2.
"""

import argparse
import logging
import signal
import threading
from types import FrameType

from app.config import get_settings

logger = logging.getLogger("lokdhara.worker")


def run(stop: threading.Event, poll_seconds: float, max_iterations: int | None = None) -> int:
    """Poll until `stop` is set. Returns the number of iterations completed."""
    iterations = 0
    while not stop.is_set():
        iterations += 1
        logger.info("worker heartbeat", extra={"iteration": iterations})
        if max_iterations is not None and iterations >= max_iterations:
            break
        stop.wait(poll_seconds)
    return iterations


def main() -> None:
    parser = argparse.ArgumentParser(description="Lokdhara background worker")
    parser.add_argument("--once", action="store_true", help="run one iteration and exit")
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    stop = threading.Event()

    def handle_signal(signum: int, _frame: FrameType | None) -> None:
        logger.info("worker stopping", extra={"signal": signum})
        stop.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    run(stop, settings.worker_poll_seconds, max_iterations=1 if args.once else None)


if __name__ == "__main__":
    main()
