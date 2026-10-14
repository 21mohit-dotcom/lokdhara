"""Accept a submission once its automatic checks pass: there is no human reviewer.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-14

The professor decided on 2026-10-14 that nobody reviews submissions by hand (ADR-021), so a
submission whose checks all succeeded is `accepted` instead of `awaiting_review`. The review
statuses stay allowed so that peer checking can use them later without dropping data.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUSES = (
    "'draft', 'uploading', 'processing', 'processing_failed', 'rejected_invalid', "
    "'awaiting_review', 'in_review', 'changes_requested', 'approved', 'rejected', 'withdrawn'"
)


def _check(statuses: str) -> None:
    op.execute("ALTER TABLE submissions DROP CONSTRAINT ck_submissions_status")
    op.execute(
        "ALTER TABLE submissions ADD CONSTRAINT ck_submissions_status "
        f"CHECK (status IN ({statuses}))"
    )


def upgrade() -> None:
    _check(f"{_STATUSES}, 'accepted'")
    op.execute("UPDATE submissions SET status = 'accepted' WHERE status = 'awaiting_review'")


def downgrade() -> None:
    op.execute("UPDATE submissions SET status = 'awaiting_review' WHERE status = 'accepted'")
    _check(_STATUSES)
