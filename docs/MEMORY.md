# Memory design

## Goals

Memory should create continuity without turning model inference into fact.

## Stores

### Canonical conversation

Flue SQLite contains the exact accepted messages, assistant outputs, and tool
events.

### Personal memory

Hindsight personal bank receives user-originated messages and explicit
corrections.

### Process memory

A separate Hindsight bank receives assistant outputs and labeled process notes.

## Retrieval

The agent can call `recall_personal_memory` with a focused query. Results are
returned in two arrays:

- `personal`;
- `process`.

The instructions require the model to treat both as fallible evidence and
process notes as lower-confidence.

## Reflection

`reflect_on_personal_history` is disabled by default because local reflection is
expensive and can produce persuasive overinterpretation. It can be enabled
after model-specific evaluation.

## Corrections

`record_memory_correction` appends an explicit user correction with strong
metadata. A complete deletion and source-level invalidation workflow remains a
required milestone before a hosted release.

## Known limitations

- Hindsight extraction quality depends on the configured model.
- Asynchronous retain means a newly stated fact may not be immediately
  retrievable.
- Append-only corrections do not physically remove older records.
- Flue currently exposes no public per-session deletion orchestration.
- Export and deletion must cover both Flue and Hindsight.

## Future work

- source IDs for every retained message;
- document-level deletion by transcript reference;
- memory review interface;
- confidence and temporal validity;
- rebuild Hindsight from canonical transcripts;
- portable encrypted export.
