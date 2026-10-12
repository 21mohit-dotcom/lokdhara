"""Append-only review events.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-11

submissions.status and restriction_flags are derived from these events and updated in the same
transaction by the review service (Milestone 6). That a reviewer never acts on their own
submission is checked in the service and by a trigger here.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RESTRICTIONS = "'sensitive', 'third_party_voice', 'contains_pii', 'culturally_restricted', 'minor'"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE review_events (
          id               uuid PRIMARY KEY DEFAULT uuidv7(),
          submission_id    uuid NOT NULL REFERENCES submissions (id),
          text_revision_id uuid REFERENCES text_revisions (id),
          reviewer_id      uuid NOT NULL REFERENCES users (id),
          action           text NOT NULL CONSTRAINT ck_review_events_action
                           CHECK (action IN ('open', 'approve', 'reject', 'request_changes',
                                  'verify_revision', 'dispute_revision', 'add_restriction',
                                  'remove_restriction', 'reopen', 'comment')),
          reason_code      text,
          restriction      text CONSTRAINT ck_review_events_restriction
                           CHECK (restriction IN ({RESTRICTIONS})),
          note             text CONSTRAINT ck_review_events_note_length
                           CHECK (char_length(note) <= 2000),
          created_at       timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT ck_review_events_restriction_actions
            CHECK ((action IN ('add_restriction', 'remove_restriction'))
                   = (restriction IS NOT NULL)),
          CONSTRAINT ck_review_events_revision_actions
            CHECK (action NOT IN ('verify_revision', 'dispute_revision')
                   OR text_revision_id IS NOT NULL)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_review_events_submission ON review_events (submission_id, created_at)"
    )
    op.execute("CREATE INDEX ix_review_events_reviewer ON review_events (reviewer_id, created_at)")
    op.execute(
        "CREATE TRIGGER review_events_append_only BEFORE UPDATE OR DELETE ON review_events "
        "FOR EACH ROW EXECUTE FUNCTION lkd_reject_change()"
    )
    op.execute(
        """
        CREATE FUNCTION lkd_reject_self_review() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.action <> 'comment' AND EXISTS (
               SELECT 1 FROM submissions
                WHERE id = NEW.submission_id AND submitted_by = NEW.reviewer_id) THEN
            RAISE EXCEPTION 'self_review: reviewers cannot act on their own submissions'
              USING ERRCODE = 'check_violation';
          END IF;
          RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER review_events_no_self_review BEFORE INSERT ON review_events "
        "FOR EACH ROW EXECUTE FUNCTION lkd_reject_self_review()"
    )


def downgrade() -> None:
    op.execute("DROP TABLE review_events")
    op.execute("DROP FUNCTION lkd_reject_self_review()")
