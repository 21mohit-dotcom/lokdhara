"""Job handlers. Audio and text handlers arrive with Milestone 4."""

from app.modules.processing.queue import JobContext, JobResult, handler


@handler("system.ping")
def ping(context: JobContext) -> JobResult:
    """Proves the queue → worker → processing_runs path works (used by `app.cli ping-worker`)."""
    return JobResult(output_summary={"pong": True, "attempt": context.attempt})
