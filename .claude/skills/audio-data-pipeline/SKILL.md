---
name: audio-data-pipeline
description: Rules and procedure for any Lokdhara code that receives, validates, stores, converts, analyses, deduplicates, or serves audio recordings. Use when touching upload endpoints, the worker's audio jobs, ffmpeg/ffprobe calls, renditions, quality metrics, audio fixtures, or object-storage keys for recordings.
---

# Audio data pipeline

Source of truth: `docs/AUDIO_PROCESSING_PIPELINE.md`, `docs/DATA_LIFECYCLE.md`, ADR-009 in `docs/ARCHITECTURE_DECISIONS.md`. Read the relevant sections before changing behaviour; if you change behaviour, update those docs in the same change.

## Invariants (never break these)

1. The original recording is written once to `originals/` after validation and is **never modified, re-encoded in place, or deleted** by processing. Only the withdrawal/erasure routine deletes originals.
2. Every derived file (rendition, peaks) records: source recording ID, source sha256, parameters, tool versions, and the `processing_runs` row that produced it.
3. File type is decided by magic bytes **and** a full FFmpeg decode — never by extension or browser MIME type.
4. Object keys contain only UUIDs and fixed names. Never use client filenames, speaker codes, or names in keys or temp paths.
5. Duplicates are flagged for human review, never deleted automatically.
6. Model-based outputs (VAD) are advisory and labelled as estimates.

## Procedure for a change

1. Identify which stage you are changing: upload (API) → validate → promote → analyse / renditions / dedupe (worker). Check the stage table in `docs/DATA_LIFECYCLE.md`.
2. Run external tools only as argument lists with a timeout, e.g.
   `subprocess.run(["ffprobe", "-v", "error", "-show_entries", "...", "-of", "json", path], capture_output=True, timeout=60, check=False)`.
   Never `shell=True`; add `-protocol_whitelist file` when reading local inputs with ffmpeg.
3. Work in a per-job temp directory; write outputs to a temp key and move into place only on success; clean up in `finally`.
4. Make jobs idempotent: re-running must not duplicate rows or change originals; renditions are keyed by `(recording_id, kind, params_hash)`.
5. Map every failure to a stable error code (`bad_signature`, `unsupported_format`, `out_of_range`, `corrupt_audio`, `too_short`, `too_long`, …). Deterministic failures reject; infrastructure failures retry with backoff.
6. Record tool versions (`ffmpeg -version` first line) in `processing_runs.tool_versions`.

## Tests to add or update

- Generate fixtures at test time with FFmpeg `lavfi` sources (e.g. `sine=frequency=220:duration=3`, `anullsrc`), in each accepted container. **Never commit audio files** (they are git-ignored and CI rejects them).
- Cover: disguised non-audio file, truncated file, too short/long, silent, clipped, stereo, 8 kHz and 96 kHz.
- Assert the original's checksum is unchanged after every job.
- Assert `processing_runs` contains tool versions.

## Smoke-tested commands (FFmpeg 6.1, planning phase)

- Analysis: `ffmpeg -hide_banner -nostats -i IN -map 0:a:0 -af "silencedetect=noise=-50dB:d=0.5,astats=metadata=0:measure_perchannel=none,ebur128=peak=true" -f null -`
- Analysis rendition: `ffmpeg -i IN -map 0:a:0 -ac 1 -ar 16000 -sample_fmt s16 -c:a flac OUT.flac`
- Playback rendition: `ffmpeg -i IN -map 0:a:0 -ac 1 -c:a libopus -b:a 24k -application voip OUT.webm`
- PCM hash: `ffmpeg -i IN -ac 1 -ar 16000 -f s16le - | sha256sum` (comparable only across the same FFmpeg version)
