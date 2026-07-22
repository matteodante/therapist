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

## Memory backend assessment

**Decision: keep Hindsight as a derived semantic index; do not replace it.**
Flue remains the canonical conversation stream and application-owned
SQLite/FTS5 remains the authority for evidence, corrections, reviewable records,
and deletion. Hindsight is justified only for the product requirement that
SQLite FTS5 does not cover: semantic, paraphrase, multilingual, and long-horizon
recall ([Flue database guide](https://flueframework.com/docs/guide/database/),
[SQLite FTS5](https://www.sqlite.org/fts5.html)).

The alternatives are capable, but none currently justifies its extra failure,
privacy, and migration surface:

| Option | Relevant strengths | Cost for this product | Decision |
| --- | --- | --- | --- |
| No sidecar | No extra service or model extraction; SQLite FTS5 provides ranked lexical retrieval. | Loses semantic and cross-language matches, which are material for longitudinal conversations. | Keep as the baseline and fallback, not the preferred product configuration. |
| Hindsight | Self-hosted MIT service, official TypeScript client, temporal/semantic recall, and cascading document deletion ([repository](https://github.com/vectorize-io/hindsight), [deletion API](https://docs.hindsight.vectorize.io/api-reference/delete-document/)) | Adds a service, database/index lifecycle, and LLM-based fact extraction. Extracted facts remain derived claims, so they cannot be authoritative for sensitive therapeutic context. | Keep behind the current structured-memory boundary; continue to exclude assistant replies, observations, and `reflect`. |
| Mem0 | Self-hosted OSS, Node SDK, configurable providers, and explicit CRUD/history through its REST service ([Node quickstart](https://docs.mem0.ai/open-source/node-quickstart), [REST API](https://docs.mem0.ai/open-source/features/rest-api)) | Duplicates the existing structured store and introduces extraction, embedding/vector configuration, and another evolving memory schema without a demonstrated advantage over Hindsight here. | Do not migrate. |
| Zep / Graphiti | Strong provenance and temporal invalidation for changing facts ([Graphiti repository](https://github.com/getzep/graphiti)) | The OSS engine is Python-first and requires a graph backend; Zep is the managed option. This is excessive for one personal agent and its small user-scoped memory. | Reject for the current scale. |
| Letta | Self-hostable stateful-agent runtime with editable memory blocks and a TypeScript client ([memory blocks](https://docs.letta.com/guides/core-concepts/memory/memory-blocks), [Docker deployment](https://docs.letta.com/guides/docker)) | It is an alternative agent runtime, not a focused memory sidecar, and would overlap with or replace Flue. Self-hosting also adds PostgreSQL/pgvector and model-provider configuration. | Reject while Flue remains the runtime. |

Self-hosting does not by itself keep sensitive text local: configured LLM and
embedding providers may still receive it. The current local configuration
avoids that external transfer, but Hindsight's official multilingual guide says
its default embedding and reranker are English-only. Before semantic recall is
treated as production-ready for Italian, configure and evaluate the documented
multilingual models and protect any network-exposed Hindsight API
([multilingual guide](https://hindsight.vectorize.io/developer/multilingual),
[configuration and authentication](https://hindsight.vectorize.io/developer/configuration)).

## Remaining requirements before hosted use

- complete Flue transcript export and deletion;
- user-facing review and editing of structured records;
- retention policy and scheduled expiry;
- encrypted portable export;
- memory-quality evaluations covering contradictions, corrections, temporal
  changes, and cross-language recall.
