"""Speakers, restricted identities, consent forms and records, withdrawal requests.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-11

Adds two column-level guards used by this and later migrations:
- lkd_guard_columns(mutable...): rows are append-only except the listed columns.
- lkd_freeze_columns(frozen...): the listed columns never change.
Both reject DELETE, and both step aside only for the erasure routine (see 0001).
See docs/DATABASE_SCHEMA.md §2.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ERASURE_BYPASS = """
  IF current_setting('lkd.erasure', true) = 'on'
     AND pg_has_role(current_user, 'app_erasure', 'MEMBER') THEN
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
  END IF;
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'append_only: DELETE on % is not allowed', TG_TABLE_NAME
      USING ERRCODE = 'insufficient_privilege';
  END IF;
"""


def upgrade() -> None:
    op.execute(
        f"""
        CREATE FUNCTION lkd_guard_columns() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          {_ERASURE_BYPASS}
          IF (to_jsonb(OLD) - TG_ARGV) IS DISTINCT FROM (to_jsonb(NEW) - TG_ARGV) THEN
            RAISE EXCEPTION 'immutable_columns: on % only % may change', TG_TABLE_NAME, TG_ARGV
              USING ERRCODE = 'insufficient_privilege';
          END IF;
          RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION lkd_freeze_columns() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
          frozen text;
        BEGIN
          {_ERASURE_BYPASS}
          FOREACH frozen IN ARRAY TG_ARGV LOOP
            IF to_jsonb(OLD) -> frozen IS DISTINCT FROM to_jsonb(NEW) -> frozen THEN
              RAISE EXCEPTION 'immutable_columns: % on % cannot change', frozen, TG_TABLE_NAME
                USING ERRCODE = 'insufficient_privilege';
            END IF;
          END LOOP;
          RETURN NEW;
        END
        $$
        """
    )

    op.execute(
        """
        CREATE TABLE speakers (
          id                     uuid PRIMARY KEY DEFAULT uuidv7(),
          speaker_code           text NOT NULL CONSTRAINT uq_speakers_speaker_code UNIQUE
                                 CONSTRAINT ck_speakers_speaker_code
                                 CHECK (speaker_code ~ '^SPK-[0-9A-Z]{5,12}$'),
          linked_user_id         uuid REFERENCES users (id),
          created_by             uuid NOT NULL REFERENCES users (id),
          age_band               text CONSTRAINT ck_speakers_age_band CHECK (age_band IN
                                 ('18-29', '30-44', '45-59', '60+', 'under_18', 'undisclosed')),
          gender_self_described  text CONSTRAINT ck_speakers_gender_length
                                 CHECK (char_length(gender_self_described) <= 60),
          first_language         text,
          other_languages        text[],
          dialect_label          text CONSTRAINT ck_speakers_dialect_length
                                 CHECK (char_length(dialect_label) <= 100),
          region_coarse          text CONSTRAINT ck_speakers_region_length
                                 CHECK (char_length(region_coarse) <= 100),
          demographics_consented boolean NOT NULL DEFAULT false,
          status                 text NOT NULL DEFAULT 'active'
                                 CONSTRAINT ck_speakers_status
                                 CHECK (status IN ('active', 'withdrawn')),
          created_at             timestamptz NOT NULL DEFAULT now(),
          -- Demographics only with consent (docs/DATA_DICTIONARY.md §1).
          CONSTRAINT ck_speakers_demographics_need_consent CHECK (
            demographics_consented OR (
              age_band IS NULL AND gender_self_described IS NULL AND first_language IS NULL
              AND other_languages IS NULL AND region_coarse IS NULL))
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_speakers_linked_user ON speakers (linked_user_id)")
    op.execute("CREATE INDEX ix_speakers_created_by ON speakers (created_by)")
    op.execute("CREATE INDEX ix_speakers_dialect ON speakers (dialect_label)")
    op.execute(
        "CREATE TRIGGER speakers_frozen BEFORE UPDATE OR DELETE ON speakers "
        "FOR EACH ROW EXECUTE FUNCTION lkd_freeze_columns('id', 'speaker_code', 'created_by')"
    )

    # Restricted: admin and the creating facilitator only. Columns hold ciphertext produced by
    # the application (key from LKD_IDENTITY_ENCRYPTION_KEY); deleted on withdrawal.
    op.execute(
        """
        CREATE TABLE speaker_identities (
          speaker_id    uuid PRIMARY KEY REFERENCES speakers (id),
          full_name_enc bytea,
          contact_enc   bytea,
          village_enc   bytea,
          notes_enc     bytea,
          key_version   integer NOT NULL DEFAULT 1,
          created_at    timestamptz NOT NULL DEFAULT now(),
          updated_at    timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    # Reporting connections never see identities, even as ciphertext.
    op.execute("REVOKE ALL ON speaker_identities FROM app_readonly")

    op.execute(
        """
        CREATE TABLE consent_forms (
          id               uuid PRIMARY KEY DEFAULT uuidv7(),
          form_code        text NOT NULL,
          version          text NOT NULL,
          language         text NOT NULL,
          text_sha256      text NOT NULL CONSTRAINT ck_consent_forms_text_sha256
                           CHECK (text_sha256 ~ '^[0-9a-f]{64}$'),
          body_markdown    text NOT NULL,
          ethics_reference text,
          is_test_form     boolean NOT NULL DEFAULT true,
          effective_from   timestamptz NOT NULL DEFAULT now(),
          retired_at       timestamptz,
          CONSTRAINT uq_consent_forms_version UNIQUE (form_code, version, language),
          CONSTRAINT ck_consent_forms_hash_matches_body
            CHECK (text_sha256 = encode(sha256(convert_to(body_markdown, 'UTF8')), 'hex'))
        )
        """
    )
    op.execute(
        "CREATE TRIGGER consent_forms_guard BEFORE UPDATE OR DELETE ON consent_forms "
        "FOR EACH ROW EXECUTE FUNCTION lkd_guard_columns('retired_at')"
    )

    op.execute(
        """
        CREATE TABLE consent_records (
          id                            uuid PRIMARY KEY DEFAULT uuidv7(),
          speaker_id                    uuid NOT NULL REFERENCES speakers (id),
          consent_form_id               uuid NOT NULL REFERENCES consent_forms (id),
          supersedes_id                 uuid REFERENCES consent_records (id),
          status                        text NOT NULL DEFAULT 'active'
                                        CONSTRAINT ck_consent_records_status
                                        CHECK (status IN ('active', 'superseded', 'withdrawn')),
          method                        text NOT NULL CONSTRAINT ck_consent_records_method
                                        CHECK (method IN
                                        ('in_app', 'oral_recorded', 'paper_reference')),
          obtained_by                   uuid NOT NULL REFERENCES users (id),
          obtained_at                   timestamptz NOT NULL DEFAULT now(),
          guardian_involved             boolean NOT NULL,
          guardian_relationship         text,
          evidence_object_key           text,
          paper_reference               text,
          allow_store_and_review        boolean NOT NULL,
          allow_research                boolean NOT NULL DEFAULT false,
          allow_public_access           boolean NOT NULL DEFAULT false,
          allow_ai_training             boolean NOT NULL DEFAULT false,
          allow_commercial_use          boolean NOT NULL DEFAULT false,
          attribution_preference        text NOT NULL DEFAULT 'pseudonymous'
                                        CONSTRAINT ck_consent_records_attribution
                                        CHECK (attribution_preference IN
                                        ('pseudonymous', 'name', 'none')),
          applies_to_past_contributions boolean NOT NULL DEFAULT false,
          notes                         text,
          CONSTRAINT ck_consent_records_store_required CHECK (allow_store_and_review),
          CONSTRAINT ck_consent_records_guardian
            CHECK (guardian_involved OR guardian_relationship IS NULL),
          CONSTRAINT ck_consent_records_oral_evidence
            CHECK (method <> 'oral_recorded' OR evidence_object_key IS NOT NULL),
          CONSTRAINT ck_consent_records_paper_reference
            CHECK (method <> 'paper_reference' OR paper_reference IS NOT NULL)
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_consent_records_one_active ON consent_records (speaker_id) "
        "WHERE status = 'active'"
    )
    op.execute("CREATE INDEX ix_consent_records_speaker ON consent_records (speaker_id, status)")
    op.execute(
        "CREATE TRIGGER consent_records_guard BEFORE UPDATE OR DELETE ON consent_records "
        "FOR EACH ROW EXECUTE FUNCTION lkd_guard_columns('status')"
    )

    op.execute(
        """
        CREATE TABLE withdrawal_requests (
          id              uuid PRIMARY KEY DEFAULT uuidv7(),
          speaker_id      uuid REFERENCES speakers (id),
          submission_id   uuid,  -- FK added with submissions (0005)
          received_via    text NOT NULL CONSTRAINT ck_withdrawal_requests_received_via
                          CHECK (received_via IN
                          ('in_app', 'facilitator', 'phone', 'in_person', 'email')),
          received_at     timestamptz NOT NULL DEFAULT now(),
          recorded_by     uuid NOT NULL REFERENCES users (id),
          requested_scope text NOT NULL CONSTRAINT ck_withdrawal_requests_scope
                          CHECK (requested_scope IN ('full', 'narrow', 'specific_items')),
          verified_by     uuid REFERENCES users (id),
          verified_at     timestamptz,
          status          text NOT NULL DEFAULT 'received'
                          CONSTRAINT ck_withdrawal_requests_status
                          CHECK (status IN
                          ('received', 'verified', 'in_progress', 'completed', 'rejected')),
          actions_taken   jsonb NOT NULL DEFAULT '[]'::jsonb,
          completed_at    timestamptz,
          CONSTRAINT ck_withdrawal_requests_has_subject
            CHECK (speaker_id IS NOT NULL OR submission_id IS NOT NULL)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_withdrawal_requests_open ON withdrawal_requests (received_at) "
        "WHERE status NOT IN ('completed', 'rejected')"
    )


def downgrade() -> None:
    for table in (
        "withdrawal_requests",
        "consent_records",
        "consent_forms",
        "speaker_identities",
        "speakers",
    ):
        op.execute(f"DROP TABLE {table}")
    op.execute("DROP FUNCTION lkd_freeze_columns()")
    op.execute("DROP FUNCTION lkd_guard_columns()")
