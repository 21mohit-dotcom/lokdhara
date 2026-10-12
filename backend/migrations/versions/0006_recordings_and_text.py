"""Recordings, renditions, text layers, and append-only text revisions.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-11

ADR-009 (originals immutable), ADR-010 (verbatim text), ADR-011 (append-only revisions with
provenance), ADR-014 (machine output is never ground truth). See docs/DATABASE_SCHEMA.md §3.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCRIPTS = "'Deva', 'Latn', 'Nagm', 'Beng', 'Orya', 'Zyyy'"
SHA256 = "~ '^[0-9a-f]{64}$'"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        f"""
        CREATE TABLE recordings (
          id                    uuid PRIMARY KEY DEFAULT uuidv7(),
          submission_id         uuid NOT NULL REFERENCES submissions (id),
          original_object_key   text NOT NULL,
          original_filename_ext text CONSTRAINT ck_recordings_ext
                                CHECK (original_filename_ext ~ '^\\.[a-z0-9]{{1,8}}$'),
          sha256_original       text NOT NULL CONSTRAINT ck_recordings_sha256_original
                                CHECK (sha256_original {SHA256}),
          sha256_pcm            text CONSTRAINT ck_recordings_sha256_pcm
                                CHECK (sha256_pcm {SHA256}),
          size_bytes            bigint NOT NULL CONSTRAINT ck_recordings_size
                                CHECK (size_bytes > 0),
          detected_container    text,
          detected_codec        text,
          sample_rate_hz        integer,
          channels              integer,
          bit_depth             integer,
          duration_ms           integer CONSTRAINT ck_recordings_duration
                                CHECK (duration_ms >= 0),
          is_lossy_source       boolean,
          upload_status         text NOT NULL DEFAULT 'quarantined'
                                CONSTRAINT ck_recordings_upload_status
                                CHECK (upload_status IN
                                ('quarantined', 'validated', 'rejected_invalid', 'promoted')),
          validation_errors     jsonb,
          quality_metrics       jsonb,
          quality_flags         text[] NOT NULL DEFAULT '{{}}'
                                CONSTRAINT ck_recordings_quality_flags
                                CHECK (quality_flags <@ ARRAY['silent', 'too_short', 'clipping',
                                       'very_quiet', 'possible_duplicate']),
          recorded_device_hint  text CONSTRAINT ck_recordings_device_hint
                                CHECK (recorded_device_hint IN ('browser_recorder', 'file_upload')),
          created_at            timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_recordings_submission ON recordings (submission_id)")
    # Not unique: duplicates are stored and flagged, never silently rejected.
    op.execute("CREATE INDEX ix_recordings_sha256_original ON recordings (sha256_original)")
    op.execute("CREATE INDEX ix_recordings_sha256_pcm ON recordings (sha256_pcm)")
    op.execute("CREATE INDEX ix_recordings_quality_flags ON recordings USING gin (quality_flags)")
    op.execute(
        "CREATE TRIGGER recordings_frozen BEFORE UPDATE OR DELETE ON recordings "
        "FOR EACH ROW EXECUTE FUNCTION lkd_freeze_columns('id', 'submission_id', "
        "'original_object_key', 'sha256_original', 'size_bytes', 'created_at')"
    )

    op.execute(
        f"""
        CREATE TABLE renditions (
          id                uuid PRIMARY KEY DEFAULT uuidv7(),
          recording_id      uuid NOT NULL REFERENCES recordings (id),
          kind              text NOT NULL CONSTRAINT ck_renditions_kind
                            CHECK (kind IN ('playback_opus', 'playback_aac',
                                   'analysis_flac_16k_mono', 'waveform_peaks')),
          object_key        text NOT NULL,
          sha256            text NOT NULL CONSTRAINT ck_renditions_sha256 CHECK (sha256 {SHA256}),
          size_bytes        bigint NOT NULL,
          params            jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          params_sha256     text NOT NULL CONSTRAINT ck_renditions_params_sha256
                            CHECK (params_sha256 {SHA256}),
          tool_versions     jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          processing_run_id uuid REFERENCES processing_runs (id),
          created_at        timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_renditions_kind_params UNIQUE (recording_id, kind, params_sha256)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER renditions_append_only BEFORE UPDATE OR DELETE ON renditions "
        "FOR EACH ROW EXECUTE FUNCTION lkd_reject_change()"
    )

    op.execute(
        f"""
        CREATE TABLE text_layers (
          id                  uuid PRIMARY KEY DEFAULT uuidv7(),
          submission_id       uuid NOT NULL REFERENCES submissions (id),
          layer_type          text NOT NULL CONSTRAINT ck_text_layers_layer_type
                              CHECK (layer_type IN ('standalone', 'transcription', 'translation')),
          recording_id        uuid REFERENCES recordings (id),
          source_layer_id     uuid REFERENCES text_layers (id),
          entry_type          text CONSTRAINT ck_text_layers_entry_type
                              CHECK (entry_type IN
                              ('word', 'phrase', 'sentence', 'paragraph', 'long_text')),
          language_tag        text NOT NULL,
          script_code         text NOT NULL CONSTRAINT ck_text_layers_script_code
                              CHECK (script_code IN ({SCRIPTS})),
          current_revision_id uuid,  -- FK added below (circular reference)
          created_at          timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT ck_text_layers_transcription_has_recording
            CHECK ((layer_type = 'transcription') = (recording_id IS NOT NULL)),
          CONSTRAINT ck_text_layers_translation_has_source
            CHECK ((layer_type = 'translation') = (source_layer_id IS NOT NULL)),
          CONSTRAINT ck_text_layers_entry_type_standalone_only
            CHECK (layer_type = 'standalone' OR entry_type IS NULL)
        )
        """
    )
    op.execute("CREATE INDEX ix_text_layers_submission ON text_layers (submission_id)")
    op.execute("CREATE INDEX ix_text_layers_source ON text_layers (source_layer_id)")
    op.execute(
        "CREATE TRIGGER text_layers_frozen BEFORE UPDATE OR DELETE ON text_layers "
        "FOR EACH ROW EXECUTE FUNCTION lkd_freeze_columns('id', 'submission_id', 'layer_type', "
        "'recording_id', 'source_layer_id', 'created_at')"
    )

    op.execute(
        f"""
        CREATE TABLE text_revisions (
          id                           uuid PRIMARY KEY DEFAULT uuidv7(),
          layer_id                     uuid NOT NULL REFERENCES text_layers (id),
          revision_number              integer NOT NULL CONSTRAINT ck_text_revisions_number
                                       CHECK (revision_number >= 1),
          based_on_revision_id         uuid REFERENCES text_revisions (id),
          source_revision_id           uuid REFERENCES text_revisions (id),
          content_original             text NOT NULL,
          content_nfc                  text NOT NULL,
          content_normalized           text,
          normalization_policy_version text,
          detected_scripts             text[] NOT NULL DEFAULT '{{}}'
                                       CONSTRAINT ck_text_revisions_detected_scripts
                                       CHECK (detected_scripts <@ ARRAY[{SCRIPTS}]),
          uncertainty_markup           boolean NOT NULL DEFAULT false,
          origin                       text NOT NULL CONSTRAINT ck_text_revisions_origin
                                       CHECK (origin IN ('human_contributor', 'human_reviewer',
                                              'machine', 'imported', 'prompt_text')),
          author_user_id               uuid REFERENCES users (id),
          tool_name                    text,
          tool_version                 text,
          model_id                     text,
          confidence                   numeric CONSTRAINT ck_text_revisions_confidence_range
                                       CHECK (confidence BETWEEN 0 AND 1),
          verification_status          text NOT NULL DEFAULT 'unverified'
                                       CONSTRAINT ck_text_revisions_verification_status
                                       CHECK (verification_status IN
                                       ('unverified', 'verified', 'disputed')),
          change_note                  text CONSTRAINT ck_text_revisions_note_length
                                       CHECK (char_length(change_note) <= 500),
          created_at                   timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_text_revisions_number UNIQUE (layer_id, revision_number),
          -- Provenance (ADR-011, ADR-014).
          CONSTRAINT ck_text_revisions_humans_have_authors
            CHECK (origin NOT IN ('human_contributor', 'human_reviewer')
                   OR author_user_id IS NOT NULL),
          CONSTRAINT ck_text_revisions_machines_name_their_tool
            CHECK (origin <> 'machine' OR (tool_name IS NOT NULL AND tool_version IS NOT NULL)),
          CONSTRAINT ck_text_revisions_confidence_only_for_machines
            CHECK (origin = 'machine' OR confidence IS NULL),
          CONSTRAINT ck_text_revisions_policy_with_normalized
            CHECK ((content_normalized IS NULL) = (normalization_policy_version IS NULL))
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_text_revisions_fts ON text_revisions "
        "USING gin (to_tsvector('simple', content_nfc))"
    )
    op.execute(
        "CREATE INDEX ix_text_revisions_trgm ON text_revisions USING gin (content_nfc gin_trgm_ops)"
    )
    op.execute("CREATE INDEX ix_text_revisions_origin ON text_revisions (origin)")
    # Revisions are append-only; only review routines change verification_status.
    op.execute(
        "CREATE TRIGGER text_revisions_guard BEFORE UPDATE OR DELETE ON text_revisions "
        "FOR EACH ROW EXECUTE FUNCTION lkd_guard_columns('verification_status')"
    )
    op.execute(
        "ALTER TABLE text_layers ADD CONSTRAINT fk_text_layers_current_revision_id_text_revisions "
        "FOREIGN KEY (current_revision_id) REFERENCES text_revisions (id)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE text_layers DROP CONSTRAINT fk_text_layers_current_revision_id_text_revisions"
    )
    op.execute("DROP TABLE text_revisions")
    op.execute("DROP TABLE text_layers")
    op.execute("DROP TABLE renditions")
    op.execute("DROP TABLE recordings")
    # pg_trgm stays installed: other objects may use it, and it holds no data.
