"""Job queue and processing history.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-11

`jobs` is a mutable work queue claimed with FOR UPDATE SKIP LOCKED (ADR-007, ADR-019).
`processing_runs` is the append-only record of every finished attempt (one row per attempt).
Payloads hold IDs only, never content or personal data.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_TYPES = (
    "'system.ping', 'audio.validate', 'audio.analyze', 'audio.renditions', 'audio.dedupe', "
    "'text.derive', 'dataset.export', 'cleanup.quarantine'"
)


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE jobs (
          id              uuid PRIMARY KEY DEFAULT uuidv7(),
          job_type        text NOT NULL
                          CONSTRAINT ck_jobs_job_type CHECK (job_type IN ({JOB_TYPES})),
          payload         jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          target_type     text,
          target_id       uuid,
          status          text NOT NULL DEFAULT 'queued'
                          CONSTRAINT ck_jobs_status
                          CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
          attempts        integer NOT NULL DEFAULT 0,
          max_attempts    integer NOT NULL DEFAULT 5 CONSTRAINT ck_jobs_max_attempts
                          CHECK (max_attempts BETWEEN 1 AND 20),
          run_after       timestamptz NOT NULL DEFAULT now(),
          dedupe_key      text,
          locked_by       text,
          lock_expires_at timestamptz,
          last_error_code text,
          created_at      timestamptz NOT NULL DEFAULT now(),
          finished_at     timestamptz
        )
        """
    )
    # Workers look for due queued jobs and expired leases.
    op.execute("CREATE INDEX ix_jobs_due ON jobs (run_after) WHERE status = 'queued'")
    op.execute("CREATE INDEX ix_jobs_leases ON jobs (lock_expires_at) WHERE status = 'running'")
    op.execute("CREATE INDEX ix_jobs_failed ON jobs (finished_at) WHERE status = 'failed'")
    op.execute("CREATE INDEX ix_jobs_target ON jobs (target_type, target_id)")
    # At most one pending job per dedupe key (e.g. one validation per recording).
    op.execute(
        "CREATE UNIQUE INDEX uq_jobs_dedupe_pending ON jobs (dedupe_key) "
        "WHERE dedupe_key IS NOT NULL AND status IN ('queued', 'running')"
    )

    op.execute(
        f"""
        CREATE TABLE processing_runs (
          id             uuid PRIMARY KEY DEFAULT uuidv7(),
          job_id         uuid,  -- no FK: finished jobs may be purged, history stays
          job_type       text NOT NULL
                         CONSTRAINT ck_processing_runs_job_type CHECK (job_type IN ({JOB_TYPES})),
          target_type    text,
          target_id      uuid,
          attempt        integer NOT NULL,
          status         text NOT NULL
                         CONSTRAINT ck_processing_runs_status
                         CHECK (status IN ('succeeded', 'failed')),
          started_at     timestamptz NOT NULL,
          finished_at    timestamptz NOT NULL,
          worker_id      text NOT NULL,
          tool_versions  jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          input_sha256   text,
          output_summary jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          error_code     text,
          error_detail   text
        )
        """
    )
    op.execute("CREATE INDEX ix_processing_runs_target ON processing_runs (target_type, target_id)")
    op.execute("CREATE INDEX ix_processing_runs_job ON processing_runs (job_id)")
    op.execute(
        "CREATE TRIGGER processing_runs_append_only BEFORE UPDATE OR DELETE ON processing_runs "
        "FOR EACH ROW EXECUTE FUNCTION lkd_reject_change()"
    )


def downgrade() -> None:
    op.execute("DROP TABLE processing_runs")
    op.execute("DROP TABLE jobs")
