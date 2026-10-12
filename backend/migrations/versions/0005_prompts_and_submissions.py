"""Prompt library (ADR-018) and submissions.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-11

See docs/DATABASE_SCHEMA.md §3 and the state machine in docs/ARCHITECTURE_DIAGRAM.md §3.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCRIPTS = "'Deva', 'Latn', 'Nagm', 'Beng', 'Orya', 'Zyyy'"
SUBMISSION_STATUSES = (
    "'draft', 'uploading', 'processing', 'processing_failed', 'rejected_invalid', "
    "'awaiting_review', 'in_review', 'changes_requested', 'approved', 'rejected', 'withdrawn'"
)
RESTRICTION_FLAGS = (
    "'sensitive', 'third_party_voice', 'contains_pii', 'culturally_restricted', 'minor'"
)


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE prompts (
          id                      uuid PRIMARY KEY DEFAULT uuidv7(),
          prompt_key              text NOT NULL CONSTRAINT ck_prompts_prompt_key
                                  CHECK (prompt_key ~ '^[a-z0-9][a-z0-9-]{{2,63}}$'),
          version                 integer NOT NULL CONSTRAINT ck_prompts_version
                                  CHECK (version >= 1),
          prompt_type             text NOT NULL CONSTRAINT ck_prompts_prompt_type
                                  CHECK (prompt_type IN ('image', 'situation', 'read_sentence')),
          text                    text,
          text_language_tag       text,
          script_code             text CONSTRAINT ck_prompts_script_code
                                  CHECK (script_code IN ({SCRIPTS})),
          image_object_key        text,
          prompt_audio_object_key text,
          source_and_licence      text NOT NULL,
          topic_tags              text[] NOT NULL DEFAULT '{{}}',
          status                  text NOT NULL DEFAULT 'draft'
                                  CONSTRAINT ck_prompts_status
                                  CHECK (status IN ('draft', 'approved', 'retired')),
          approved_by             uuid REFERENCES users (id),
          created_by              uuid NOT NULL REFERENCES users (id),
          created_at              timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_prompts_key_version UNIQUE (prompt_key, version),
          CONSTRAINT ck_prompts_image_has_image
            CHECK (prompt_type <> 'image' OR image_object_key IS NOT NULL),
          CONSTRAINT ck_prompts_situation_has_text
            CHECK (prompt_type <> 'situation' OR text IS NOT NULL),
          CONSTRAINT ck_prompts_sentence_has_text_and_script
            CHECK (prompt_type <> 'read_sentence'
                   OR (text IS NOT NULL AND script_code IS NOT NULL)),
          CONSTRAINT ck_prompts_approval_recorded
            CHECK (status = 'draft' OR approved_by IS NOT NULL)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_prompts_pick ON prompts (prompt_type, script_code) "
        "WHERE status = 'approved'"
    )
    op.execute("CREATE INDEX ix_prompts_topics ON prompts USING gin (topic_tags)")
    # Editing a prompt creates a new version; only approval and retirement change a row.
    op.execute(
        "CREATE TRIGGER prompts_guard BEFORE UPDATE OR DELETE ON prompts "
        "FOR EACH ROW EXECUTE FUNCTION lkd_guard_columns('status', 'approved_by')"
    )

    op.execute(
        f"""
        CREATE TABLE submissions (
          id                   uuid PRIMARY KEY DEFAULT uuidv7(),
          client_submission_id uuid NOT NULL
                               CONSTRAINT uq_submissions_client_submission_id UNIQUE,
          submitted_by         uuid NOT NULL REFERENCES users (id),
          speaker_id           uuid NOT NULL REFERENCES speakers (id),
          consent_record_id    uuid REFERENCES consent_records (id),
          kind                 text NOT NULL CONSTRAINT ck_submissions_kind
                               CHECK (kind IN ('audio', 'text', 'audio_text')),
          content_type         text NOT NULL CONSTRAINT ck_submissions_content_type
                               CHECK (content_type IN ('story', 'conversation', 'vocabulary',
                                                       'song', 'sentence_list', 'other')),
          title                text CONSTRAINT ck_submissions_title_length
                               CHECK (char_length(title) <= 200),
          language_tag         text NOT NULL DEFAULT 'unr',
          dialect_label        text CONSTRAINT ck_submissions_dialect_length
                               CHECK (char_length(dialect_label) <= 100),
          region_coarse        text CONSTRAINT ck_submissions_region_length
                               CHECK (char_length(region_coarse) <= 100),
          recorded_on          date,
          recording_mode       text CONSTRAINT ck_submissions_recording_mode
                               CHECK (recording_mode IN ('free', 'prompted', 'read')),
          prompt_id            uuid REFERENCES prompts (id),
          collection_method    text NOT NULL CONSTRAINT ck_submissions_collection_method
                               CHECK (collection_method IN ('self_recorded', 'facilitator_field',
                                      'facilitator_remote', 'imported_archive')),
          collection_context   jsonb NOT NULL DEFAULT '{{}}'::jsonb
                               CONSTRAINT ck_submissions_context_is_object
                               CHECK (jsonb_typeof(collection_context) = 'object'),
          status               text NOT NULL DEFAULT 'draft'
                               CONSTRAINT ck_submissions_status
                               CHECK (status IN ({SUBMISSION_STATUSES})),
          restriction_flags    text[] NOT NULL DEFAULT '{{}}'
                               CONSTRAINT ck_submissions_restriction_flags
                               CHECK (restriction_flags <@ ARRAY[{RESTRICTION_FLAGS}]),
          created_at           timestamptz NOT NULL DEFAULT now(),
          submitted_at         timestamptz,
          updated_at           timestamptz NOT NULL DEFAULT now(),
          -- No submission leaves draft without consent (docs/CONSENT_AND_DATA_GOVERNANCE.md).
          CONSTRAINT ck_submissions_consent_before_submit
            CHECK (status IN ('draft', 'withdrawn') OR consent_record_id IS NOT NULL),
          -- Audio needs a recording mode; text-only submissions have none (ADR-018).
          CONSTRAINT ck_submissions_mode_matches_kind
            CHECK ((kind = 'text') = (recording_mode IS NULL)),
          CONSTRAINT ck_submissions_prompt_matches_mode
            CHECK ((recording_mode IN ('prompted', 'read')) = (prompt_id IS NOT NULL))
        )
        """
    )
    op.execute("CREATE INDEX ix_submissions_submitted_by ON submissions (submitted_by, status)")
    op.execute("CREATE INDEX ix_submissions_speaker ON submissions (speaker_id)")
    op.execute("CREATE INDEX ix_submissions_status ON submissions (status, submitted_at)")
    op.execute("CREATE INDEX ix_submissions_filters ON submissions (content_type, dialect_label)")
    op.execute(
        "CREATE INDEX ix_submissions_restrictions ON submissions USING gin (restriction_flags)"
    )
    op.execute(
        "CREATE TRIGGER submissions_frozen BEFORE UPDATE OR DELETE ON submissions "
        "FOR EACH ROW EXECUTE FUNCTION "
        "lkd_freeze_columns('id', 'client_submission_id', 'submitted_by', 'created_at')"
    )

    op.execute(
        "ALTER TABLE withdrawal_requests ADD CONSTRAINT "
        "fk_withdrawal_requests_submission_id_submissions "
        "FOREIGN KEY (submission_id) REFERENCES submissions (id)"
    )

    op.execute(
        """
        CREATE TABLE related_items (
          id           uuid PRIMARY KEY DEFAULT uuidv7(),
          submission_a uuid NOT NULL REFERENCES submissions (id),
          submission_b uuid NOT NULL REFERENCES submissions (id),
          relation     text NOT NULL CONSTRAINT ck_related_items_relation
                       CHECK (relation IN
                       ('same_story_retake', 'possible_duplicate', 'continuation')),
          created_by   uuid REFERENCES users (id),
          created_at   timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT ck_related_items_distinct CHECK (submission_a <> submission_b),
          CONSTRAINT uq_related_items_pair UNIQUE (submission_a, submission_b, relation)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE related_items")
    op.execute(
        "ALTER TABLE withdrawal_requests "
        "DROP CONSTRAINT fk_withdrawal_requests_submission_id_submissions"
    )
    op.execute("DROP TABLE submissions")
    op.execute("DROP TABLE prompts")
