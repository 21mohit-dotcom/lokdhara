---
name: privacy-review
description: Checklist for reviewing any Lokdhara change that touches personal data, speaker identity, consent, access control, authentication, uploads, logging, exports, dataset releases, withdrawals, or third-party services. Use before committing such a change, when designing a feature that handles contributor data, or when asked for a privacy or security review.
---

# Privacy, consent, and security review

Source of truth: `docs/PRIVACY_AND_SECURITY.md`, `docs/CONSENT_AND_DATA_GOVERNANCE.md`, `docs/ACCESS_CONTROL.md`, `docs/DATA_RETENTION_AND_DELETION.md`.

These documents describe controls, not legal compliance. Never write code comments, docs, or UI text claiming the platform is "compliant", "GDPR/DPDP compliant", or "fully anonymous".

## Review checklist

Answer each item for the change under review; report every "no" or "unsure" with file:line.

**Data minimisation**
- [ ] Does the change collect or store any new personal, demographic, or location data? If yes, is it in `docs/DATA_DICTIONARY.md` with a consent basis?
- [ ] Are free-text fields that may contain personal details kept out of exports and logs?

**Consent and access**
- [ ] Can any item become visible, playable, searchable, or exportable to someone the speaker's consent does not allow? All read paths must use the effective-access rule.
- [ ] Are restriction flags (`sensitive`, `third_party_voice`, `contains_pii`, `culturally_restricted`, `minor`) honoured?
- [ ] Does narrowing or withdrawal of consent propagate to this feature?
- [ ] Are role checks done server-side in the service layer (not only in the UI)?
- [ ] Can a reviewer act on their own submission? (Must be no.)

**Storage and transport**
- [ ] Restricted data stays in restricted tables/buckets; consent evidence stays in its own bucket.
- [ ] Object keys and paths contain no names or client filenames.
- [ ] Signed URLs are short-lived; originals are admin-only and audited.

**Logging and audit**
- [ ] No audio, text content, names, contacts, tokens, cookies, or raw IPs in logs or error messages.
- [ ] Privileged and restricted-data actions write `audit_events`.

**Uploads and input**
- [ ] Size limits, magic-byte + decode validation, server-generated keys, isolated processing.
- [ ] Text input rejects control and bidi-override characters; output rendered as text.

**Exports and releases**
- [ ] Export fields come from the explicit allow-list only.
- [ ] Release purpose gates on the right consent flag.

**Repository**
- [ ] No real data, `.env`, keys, dumps, or audio in the diff (`git diff --cached --name-only`).

**Third parties**
- [ ] Does the change send any data to an external service (analytics, error tracking, AI APIs, auth providers)? If yes, it needs an ADR and owner approval.

## Output

Summarise: risks found (severity, file:line, fix), items needing a decision by the professor/institution/community (link the open-question ID in `docs/ASSUMPTIONS_AND_OPEN_QUESTIONS.md`, or add a new one), and tests that prove the controls.
