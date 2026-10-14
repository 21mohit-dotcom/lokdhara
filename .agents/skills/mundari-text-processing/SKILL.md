---
name: mundari-text-processing
description: Rules for handling Mundari, Hindi, and English text in Lokdhara — validation, Unicode normalisation, script detection, transcription and translation revisions, provenance, uncertainty markup, and text duplicate checks. Use when touching text input validation, text_layers/text_revisions, search over text, export of text, or anything involving Devanagari, Latin, or Nag Mundari script.
---

# Mundari text processing

Source of truth: `docs/TEXT_PROCESSING_PIPELINE.md`, `docs/DATA_DICTIONARY.md`, ADR-010 and ADR-011.

## Core rules

1. **Store verbatim.** `content_original` is exactly what the person submitted. Reject unsafe input (invalid UTF-8, disallowed control or bidi-override characters, length limits); never silently "fix" it.
2. **No single correct orthography.** Mundari is written in Devanagari (`Deva`), Latin (`Latn`), Nag Mundari / Mundari Bani (`Nagm`, U+1E4D0–U+1E4FF), and possibly others. Do not convert between scripts or "correct" spellings in stored data.
3. **Derived fields are separate.** `content_nfc` = Unicode NFC. Never use NFKC/NFKD. `content_normalized` stays NULL until a versioned, linguist-approved policy exists (open question Q-X2).
4. **Keep ZWJ (U+200D) and ZWNJ (U+200C).** They change rendering in Indic scripts.
5. **Every change is a new revision** in `text_revisions` with `origin` (`human_contributor`, `human_reviewer`, `machine`, `imported`), author or tool/model/version, and `based_on_revision_id`. Never UPDATE content.
6. **Machine output is never verified by default.** `origin = machine` requires tool name, version, and model ID; it stays `unverified` until a human revision supersedes it.
7. Translations link to their source layer and store `source_revision_id` so stale translations can be detected.
8. Declared script vs. detected script mismatch → warn, never auto-correct.

## Procedure

1. Put text logic in pure functions under `backend/app/text/` (validate, nfc, detect_scripts, parse_uncertainty_markup). No DB access in them.
2. Use `unicodedata.normalize("NFC", s)`; use the `regex` package for `\p{Script=...}` checks. Confirm the Python Unicode database includes Nag Mundari (Unicode ≥ 15.0; Python 3.13 has 15.1).
3. Search and dedupe use `content_nfc` with whitespace collapsed; near-duplicates of words across speakers are valuable variation — flag, don't merge.
4. Uncertainty markup (`[?word]`, `[inaudible]`, `[overlap]`, `[hi: …]`, `[noise]`) is parsed by one tested function; a revision with unresolved uncertainty cannot be marked `verified`.

## Tests

- Hypothesis property tests: NFC idempotent; original preserved byte-for-byte; disallowed characters always rejected; ZWJ/ZWNJ preserved.
- Example tests in all supported scripts, mixed-script text, and combining sequences.
- Revision tests: append-only, attribution required, 409 on stale `base_revision_id`.
- Use synthetic or public-domain sample strings only; never paste collected community text into tests.
