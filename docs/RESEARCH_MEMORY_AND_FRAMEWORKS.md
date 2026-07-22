# Research: memory and frameworks for Therapist

Date: July 22, 2026.

## Conclusion

The MVP should keep Flue and Hindsight, but Hindsight should remain a secondary
retrieval index rather than the source of clinical truth. User-confirmed data,
including profile information, goals, preferences, corrections, and consent,
should live in structured, inspectable, and editable application storage. Flue
remains the canonical transcript store.

## What Flue prescribes

Flue uses its database for the canonical conversation stream, attachments,
submissions, and workflow runs. It explicitly states that application data
belongs in the application or external systems. For Node deployments, it
recommends SQLite on a single host and Postgres when shared persistence or
multiple replicas are required. Flue neither prescribes Hindsight nor provides
integrated long-term semantic memory.

Sources:

- [Flue: Database](https://flueframework.com/docs/guide/database/)
- [Flue: Data Persistence API](https://flueframework.com/docs/api/data-persistence-api/)
- [Flue: Durable Agents](https://flueframework.com/docs/concepts/durable-execution/)
- [Flue: Tools](https://flueframework.com/docs/guide/tools/)

## Hindsight assessment

Hindsight provides `retain`, `recall`, and `reflect`, fact and entity
extraction, temporal reasoning, and multi-strategy retrieval. It is open
source, self-hostable, and has a TypeScript client. It reports strong results
on general long-term-memory benchmarks.

Those benchmarks do not establish clinical suitability, health-data safety,
multilingual correctness, or freedom from extraction bias. Therapist should
use `retain` and `recall` with explicit provenance and corrections while
keeping observations and `reflect` disabled until task-specific evaluations
exist. Complete deletion, retention controls, authentication, auditing, and
per-user isolation are also required.

Sources:

- [Hindsight: official repository and documentation](https://github.com/vectorize-io/hindsight)
- [Hindsight Cloud: Retain, Recall, and Reflect](https://docs.hindsight.vectorize.io/)
- [Hindsight: stated benchmark limitations](https://hindsight.vectorize.io/blog/2026/03/23/agent-memory-benchmark)

## Alternatives to Flue

### Mastra

Mastra is the most cohesive TypeScript alternative when reducing the number of
services is the priority. It integrates agents, workflows, memory, storage,
semantic recall, evaluations, and observability. It could replace parts of both
the harness and the external-memory service. Migration would still be costly
and would require rebuilding the existing Telegram channel, security boundary,
and persistence integration.

- [Mastra](https://mastra.ai/)
- [Mastra: agent memory](https://mastra.ai/blog/agent-memory-guide)

### LangGraph.js

LangGraph.js is preferable when behavior must be an explicit state machine
with checkpoints, pauses, human-in-the-loop control, and inspectable paths. It
distinguishes short-term checkpointers from long-term stores. For a clinically
sensitive product, that gives tighter flow control at the cost of more code and
orchestration.

- [LangGraph.js: persistence](https://langchain-ai.github.io/langgraphjs/how-tos/subgraph-persistence/)

### OpenAI Agents SDK

This is a good option if the product adopts OpenAI as its primary platform. It
provides persistent sessions, configurable providers, and tracing, but makes a
local-first Ollama target less natural and does not itself solve structured
clinical memory.

- [OpenAI Agents SDK: Sessions](https://openai.github.io/openai-agents-js/guides/sessions/)
- [OpenAI Agents SDK: Models](https://openai.github.io/openai-agents-js/guides/models/)

## Operational recommendation

1. Keep Flue as the canonical transcript and MVP runtime.
2. Keep Hindsight as secondary retrieval, with `reflect` and automatic
   observations disabled.
3. Add structured application memory only for user-confirmed data, including
   provenance, timestamps, correction, and deletion.
4. Evaluate Hindsight with English and Italian scenarios covering
   contradictions, corrections, temporal events, ambiguous names, false
   memories, and clinical risk.
5. Reconsider Mastra if stack simplification becomes the priority; reconsider
   LangGraph if an explicit and verifiable clinical protocol becomes the
   priority.
