# Memory design

## Principle

Memory provides continuity without promoting model inference to fact. No single
memory layer is trusted for every purpose.

## Stores

### Canonical conversation

Flue SQLite stores the accepted messages, assistant output, tool calls, and
tool results. It is the canonical record of what happened.

### Structured application memory

`therapist-app.db` stores concise goals, preferences, interventions, outcomes,
open questions, repairs, tentative working hypotheses, and explicit
corrections. Each record includes the supporting user evidence. Structured
records take precedence over semantic recall when they conflict.

### Hindsight derived index

One user-scoped Hindsight bank indexes user-originated Telegram messages and
explicit corrections. It never stores complete assistant responses. Messages
are appended to stable documents through Hindsight's native `documentId` and
`updateMode: "append"` support, making the index replaceable and deletable.

Hindsight remains a fallible retrieval accelerator, not a source of clinical
truth. Automatic observations and `reflect` are not used.

## Retrieval

`recall_personal_memory` returns two clearly labeled collections:

- `structured`: application-owned records with evidence and timestamps;
- `semantic`: Hindsight facts with context, document ID, and mention time.

The agent must prefer structured records and treat semantic results as
potentially incomplete or distorted.

## Corrections

`record_memory_correction` writes an authoritative structured correction and
also appends it to a dedicated Hindsight correction document so retrieval can
surface it. The structured correction wins over conflicting extracted facts.

## Deletion

`/clear-derived-memory confirm` deletes structured application memory and the
two known Hindsight documents through Hindsight's native document deletion API.
It intentionally does not claim to delete Flue's canonical conversation stream,
because the pinned Flue version exposes no public per-session deletion
orchestration.

## Remaining requirements before hosted use

- complete Flue transcript export and deletion;
- user-facing review and editing of structured records;
- retention policy and scheduled expiry;
- encrypted portable export;
- memory-quality evaluations covering contradictions, corrections, temporal
  changes, and cross-language recall.
