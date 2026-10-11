import threading

from app.worker import run


def test_worker_runs_requested_iterations() -> None:
    assert run(threading.Event(), poll_seconds=0.01, max_iterations=3) == 3


def test_worker_stops_when_signalled() -> None:
    stop = threading.Event()
    stop.set()
    assert run(stop, poll_seconds=0.01) == 0
