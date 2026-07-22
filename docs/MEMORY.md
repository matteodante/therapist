# Memory design

## Decision

Therapist uses a plain Markdown vault. There is no semantic memory service,
embedding model, vector store, or automatic extraction pipeline.

Flue SQLite remains the canonical conversation stream. The vault contains only
curated long-term memory that should affect future conversations.

## Vault

The directory configured by `THERAPIST_MEMORY_PATH` contains two notes:

```text
memory/
  SELF.md
  JOURNEY.md
```

### `SELF.md`

User-owned context: durable facts, relationships, values, preferences, and
other information explicitly stated or confirmed by the user. Assistant
inferences never belong here.

### `JOURNEY.md`

Collaborative process memory organized into goals, tentative working
hypotheses, experiments, outcomes, open threads, and repairs. These are
assistant-authored notes with supporting user evidence, not facts about the
user.

There is no separate profile, active-memory, correction, or session-note file.
Corrections update the affected bullet in place. Flue already stores the full
session history, so copying transcripts or session summaries into the vault
would create a second source of truth.

## Tools

- `read_therapy_memory` reads both concise notes in full.
- `remember_user_context` appends one user-stated item to `SELF.md`.
- `record_therapy_process_note` adds one item to the appropriate `JOURNEY.md`
  section.
- `correct_therapy_memory` replaces an exact excerpt in an existing bullet.

The model never receives generic filesystem access. Trusted application code
selects the directory and filenames, validates tool inputs, normalizes entries,
and performs same-directory temporary-file renames for writes.

## User access

The vault is ordinary Markdown and can be opened directly in Obsidian or any
text editor. `data/` is excluded from Git. Docker bind-mounts `./data` so the
same files remain accessible from the host.

## Deletion

`/clear-memory confirm` resets both notes and reports how many memory bullets
were removed. It does not delete Flue's canonical conversation stream.

## Deliberate limit

Reading two concise notes is sufficient for the single-user product. Add a
rebuildable local index only after measured context growth or recall failures;
do not make an index authoritative.
