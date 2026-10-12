"""Job handlers. Importing this module registers every handler with the queue."""

from app.modules.processing.queue import JobContext, JobResult, handler
from app.modules.submissions import processing  # noqa: F401 - audio.validate, cleanup.quarantine


@handler("system.ping")
def ping(context: JobContext) -> JobResult:
    """Proves the queue → worker → processing_runs path works (used by `app.cli ping-worker`)."""
    return JobResult(output_summary={"pong": True, "attempt": context.attempt})
