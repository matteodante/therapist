# Unreleased clean-break refactor

This is an engineering change record, not a published release or clinical-validation claim.

- Separated root protocol, verified skill catalog, dynamically loaded skill body, successful
  history, and bounded JSON case data.
- Expanded the experimental pack to fifteen conversational-process skills; status remains
  `experimental`, with no reviewers invented.
- Rewrote every skill in positive form: entry conditions first, then procedure, then the remaining
  prohibitions. Added staying with emotion, self-criticism and shame, examining one thought,
  repetitive thinking, and restoring activity, and gave the root explicit rules for answering
  competence questions, life questions, and direct questions, plus a precedence order for choosing
  among skills.
- Allowed a preference or pattern to shorten its evidence quote by dropping the user's own words in
  their original order, recorded as `grounded_paraphrase`; facts and events still store the quote
  verbatim. No quoted field may be taken out of the clause that qualified it, including intervention
  consent. Correcting or forgetting a restated claim now retires the quotes that supported it.
- Added a maintainer tool for recomputing manifest digests, removed unused per-skill agent interface
  descriptors, and moved background research out of `protocols/` into `docs/research/`.
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
