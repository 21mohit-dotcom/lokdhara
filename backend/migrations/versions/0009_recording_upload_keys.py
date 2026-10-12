"""Remember each upload's Idempotency-Key so a retried upload is stored only once.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-12

Phones on weak connections often resend an upload whose response was lost. The SPA sends the
same Idempotency-Key with every retry of one file; the API returns the recording it already
stored for that key instead of storing the audio again (docs/API_SPECIFICATION.md §1, §4).
The key is part of the recording's frozen identity.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FROZEN = "'id', 'submission_id', 'original_object_key', 'sha256_original', 'size_bytes'"


def upgrade() -> None:
    # Nullable: recordings imported from archives would not arrive through the upload API.
    op.execute("ALTER TABLE recordings ADD COLUMN upload_key uuid")
    op.execute(
        "CREATE UNIQUE INDEX uq_recordings_upload_key ON recordings (submission_id, upload_key)"
    )
    op.execute("DROP TRIGGER recordings_frozen ON recordings")
    op.execute(
        "CREATE TRIGGER recordings_frozen BEFORE UPDATE OR DELETE ON recordings "
        f"FOR EACH ROW EXECUTE FUNCTION lkd_freeze_columns({_FROZEN}, 'upload_key', "
        "'created_at')"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER recordings_frozen ON recordings")
    op.execute(
        "CREATE TRIGGER recordings_frozen BEFORE UPDATE OR DELETE ON recordings "
        f"FOR EACH ROW EXECUTE FUNCTION lkd_freeze_columns({_FROZEN}, 'created_at')"
    )
    op.execute("DROP INDEX uq_recordings_upload_key")
    op.execute("ALTER TABLE recordings DROP COLUMN upload_key")
