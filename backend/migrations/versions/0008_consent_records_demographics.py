"""Record the demographics answer on each consent record.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-12

The consent model asks seven questions (docs/CONSENT_AND_DATA_GOVERNANCE.md §3.1); 0004 stored
six of them. speakers.demographics_consented mirrors the active record's answer, but only the
append-only consent record shows what the speaker agreed to and when.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE consent_records "
        "ADD COLUMN demographics_consented boolean NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE consent_records DROP COLUMN demographics_consented")
