# Unreleased clean-break refactor

This is an engineering change record, not a published release or clinical-validation claim.

- Separated root protocol, verified skill catalog, dynamically loaded skill body, successful
  history, and bounded JSON case data.
- Expanded the experimental pack to ten conversational-process skills; status remains
  `experimental`, with no reviewers invented.
- Replaced overloaded memory status with independent origin, fit, lifecycle, evidence relation,
  conflict, and staleness semantics.
- Added exact-evidence tools for user reports, hypotheses, corrections, reviews, conversational
  preferences, interventions/outcomes/unwanted effects, focus, and support choices.
- Added structured retrieval for reports, hypotheses, conflicts, sessions, preferences,
  interventions, support choices, and excerpts.
- Replaced the one-call-per-tool restriction with cumulative turn invariants. Repeated reads and
  distinct evidence-supported writes remain bounded, idempotent, and atomically committed.
- Added standard, transcript-only, and ephemeral modes; optional local retention; session/date
  deletion; a 4,000-character reply cap; and observable turn metadata.
- This revision intentionally provides no migration or legacy compatibility. Old stores are
  rejected without modification and require a fresh data directory.
- Updated consent/privacy text, deterministic tests, bilingual role-play specifications, and the
  exportable human-review artifact.

Remaining limitations include no clinical review or validation, no background retention worker, no
provider/Telegram deletion control, and opt-in-only live provider evaluation.
