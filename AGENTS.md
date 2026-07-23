# Therapist project guide

This file is the canonical source of truth for the project's purpose, scope, architecture, and
working rules. Keep it updated in the same change whenever behavior, commands, storage, scope,
architecture, dependencies, licensing, or milestones change. `README.md` is the concise public
overview; keep it synchronized with this canonical guide when user-visible behavior changes.

## Project idea

Therapist is an experimental, self-hosted AI conversation agent that reproduces the useful
process qualities of a therapist: careful listening, longitudinal continuity, collaborative case
formulation, pattern recognition, gentle challenge, and selection of an appropriate next step.

It remains explicitly an AI. It must not claim to be a psychologist or psychotherapist, diagnose,
prescribe, promise recovery, present itself as an emergency service, or imply human monitoring.

The long-term product may support both self-hosted and SaaS distribution. The current milestone is
deliberately smaller: make the single-user conversation and long-term memory work well through the
local CLI and one private Telegram transport before building broader infrastructure.

Original code and project content are open source under `AGPL-3.0-or-later`. Linked or referenced
third-party materials remain under their owners' terms and are not relicensed by this repository.

## Current scope

Build a small bilingual, single-user agent that:

- holds a warm, active, natural conversation in Italian or English;
- identifies user-stated difficulties and recurring patterns without requiring predefined goals;
- builds a visible, correctable, evidence-linked case formulation;
- keeps direct facts tied to exact user evidence, mutates corrected claims in place, and keeps focus
  proposed only within the current session until accepted;
- remembers relevant context across weeks, months, and years;
- keeps the complete archive and structured memory encrypted on the local machine;
- works with local or remote model providers through PydanticAI;
- optionally uses a personal ChatGPT Plus/Pro Codex subscription through experimental OAuth;
- versions behavioral instructions and source references in a protocol pack;
- lets the user inspect, confirm, correct, forget, export, and delete memory;
- records offered, agreed, tried, stopped, and untried interventions for later review;
- accepts the same therapeutic conversation through a private, allowlisted Telegram bot;
- remains small enough for one maintainer to understand.

Included in this milestone:

- interactive terminal chat;
- private text-only Telegram chat using long polling and the standard Bot API;
- one PydanticAI conversational agent and one end-of-session consolidation pass;
- device-code ChatGPT OAuth, encrypted token storage, and automatic refresh for the experimental
  `codex:` provider;
- encrypted SQLite archive and layered longitudinal memory;
- automatic session boundaries after eight hours of inactivity and explicit `/end`;
- an experimental bilingual transdiagnostic behavior pack;
- a minimal Italian/US explicit-danger fallback;
- offline tests using PydanticAI test models.
- written, versioned longitudinal-memory scenarios plus an opt-in real-provider test.

Explicitly deferred:

- web, mobile, voice, Telegram groups/media/webhooks, and other channels;
- SaaS, accounts, billing, multi-tenancy, PostgreSQL, workers, and queues;
- reminders, background jobs, MCP integrations, and external tools;
- standalone vector databases, knowledge graphs, and multi-agent orchestration;
- commercial dual licensing, a CLA, and formal release/PyPI publishing;
- clinical ownership, clinical validation, efficacy studies, and formal risk management;
- MDR, AI Act, FDA, GDPR/HIPAA compliance work;
- formal threat modeling, penetration tests, audits, and certifications.

The alpha retains baseline safeguards already present: transparent AI identity, no clinical claims,
and emergency resources after an explicit danger disclosure. These are not a validated clinical
safety system.

## Therapeutic behavior

The agent uses an integrative, transdiagnostic approach informed by CBT formulation, ACT-style
flexibility, behavioral activation, emotional awareness, and problem solving.

Its loop is:

1. listen and clarify;
2. explore emotions, triggers, thoughts, behavior, relationships, and coping;
3. form a tentative, evidence-linked hypothesis;
4. share the hypothesis and ask whether it fits;
5. agree on an intervention or next conversational focus;
6. observe the user's response;
7. revise the formulation rather than defending it.

Behavioral rules:

- respond in the user's language;
- respond to the user's immediate meaning before suggesting an action, without mechanically
  paraphrasing every message;
- ask brief, concrete questions and avoid interrogation;
- identify recurring themes and inconsistencies with a gentle, collaborative tone;
- label interpretations as hypotheses until the user confirms them;
- ask permission before exercises;
- when the user asks for understanding before suggestions, offer at most one brief hypothesis and
  keep exploring instead of listing explanations or introducing an exercise;
- do not force a goal, worksheet, or technique onto every exchange;
- use the therapeutic protocol as an internal map rather than a visible sequence; questions,
  hypotheses, formulation, and forward movement are optional when simple presence is more useful;
- vary response length, rhythm, and conversational move instead of repeating a
  reflection-hypothesis-question template;
- prefer the smallest useful intervention;
- do not use diagnostic labels or claim knowledge unsupported by the archive;
- do not encourage exclusivity, dependency, or withdrawal from human support.

## Architecture

```text
User
  |
  v
CLI or private Telegram -> deterministic explicit-danger fallback -> 112 / 911 / 988
  |
  v
Versioned experimental behavior pack
  |
  v
PydanticAI tool loop + plain-text reply -> local model or configured remote provider
  |
  v
Encrypted SQLite archive + structured longitudinal memory
```

Use one PydanticAI agent run per normal turn. The agent returns the visible reply as plain text and
uses six bounded function tools: one optional read-only longitudinal-memory search plus staged tools
for memory observations, corrections, hypothesis confirmations, focus, and one intervention update.
Tools validate and buffer actions but never mutate SQLite during the model run. After a valid final
reply, the transcript and all staged actions are committed in one transaction; failure leaves both
unchanged. Tool exchanges are not retained in model history, which stores only the canonical
user/assistant pair.

A normal run permits at most eight model requests, six successful tool calls, and two output retries
within that global budget. All model-written strings and collections have size limits. Accepted
focus, confirmed hypotheses, and agreed or updated interventions require exact supporting text from
the current user message. The IDs of the last explicitly offered hypothesis and active intervention
remain pending so confirmation, agreement, and outcome update the original records instead of
creating copies. Provider transport retries remain a separate concern.

When a session closes, use one additional structured model call to summarize the episode and link
existing claims into the case formulation. Consolidation allows two output retries and at most three
model requests. It cannot create a confirmed claim. If it fails, preserve the transcript, record a
content-free error class, and leave the previous formulation intact. Both agent runs use PydanticAI's
complete synchronous API with an event stream handler so the experimental ChatGPT Codex backend can
require `stream=true`; the CLI prints only the validated final reply.

Consolidation preserves valid formulation links when the model omits them and removes a link only
through an explicit `formulation_unlinks` entry. Existing evidence is retained before new links when
a field reaches its five-claim bound, so omission or overflow cannot silently evict history.

Memory retrieval uses local hybrid ranking over validated claims by default: lexical overlap plus
semantic similarity through PydanticAI `Embedder`, with recency as a tie-breaker. The semantic index
is an encrypted, derived SQLite cache tied to claim IDs and keyed content hashes; it is rebuilt after
content or model changes and deleted on forgetting. SQLite/Fernet remains the source of truth.
Semantic retrieval is a required memory capability: setup downloads and verifies the local model,
and conversation fails closed with setup guidance when embeddings are unavailable rather than
silently switching to lexical-only claim ranking. Historical excerpts remain lexical and prefer
recency on equal scores. Context is reduced by complete structured items and serialized only as
valid JSON; model history and consolidation retain complete turns instead of slicing messages
mid-run.

## Memory model

Memory is layered so that "remember everything" does not mean sending the entire archive to the
model on every turn.

- `Message`: complete encrypted user/assistant archive retained until deletion.
- `Session`: time-bounded episode with summary, themes, interventions, user response, and open
  questions.
- `MemoryItem`: a durable fact, preference, consequential event, pattern, or hypothesis with
  provenance and timestamps; a turn may write at most two.
- `CaseFormulation`: an evidence map that derives concerns, triggers, thoughts, behavior, coping,
  relationships, course, functioning, explanatory model, preferences, maintaining factors,
  strengths, hypotheses, and focus from active memory claim IDs.
- `InterventionRecord`: one offered or agreed technique with consent state, linked claims,
  prediction, outcome, user appraisal, and follow-up information. It is not a goal.
- `WorkingContext`: formulation, bounded confirmed memory, unresolved hypotheses, the latest three
  completed sessions, at most five active interventions, and five historical excerpts.
- `SemanticIndex`: encrypted vectors for active `MemoryItem` records only. It is derived,
  excluded from export, safe to discard, and never establishes truth or provenance.

Memory states:

- `user_confirmed`: directly stated or explicitly confirmed by the user;
- `agent_hypothesis`: an interpretation that must remain tentative;
- `user_corrected`: a user correction that overrides older inferences;
- `archived`: excluded from future context while retained in the user's export until full deletion.

The complete archive is retained until the user deletes it. Corrections and forgotten items must be
removed from derived formulation and summaries and suppressed from future retrieval. Current-session
model history is bounded; long-term continuity comes from structured context and relevant excerpts.
When generated derived text paraphrases corrected or forgotten evidence, the overlapping derived
field is conservatively invalidated instead of risking stale personal information returning.
Explicit corrections from natural conversation target an existing claim ID, retain the old wording
as superseded provenance, clear stale aliases, and cannot also create a replacement claim.
If forgetting removes the meaningful description of an intervention, its sensitive content is
replaced with a neutral tombstone and the record is stopped rather than deleted, preserving lifecycle
and provenance without returning forgotten content.

Session activity timestamps are written both to the indexed SQLite column and the encrypted session
payload in the same transaction so restart cannot move the eight-hour boundary backward. SQLite
comes from the Python standard library. Sensitive payloads are encrypted with Fernet using a
separate local key with filesystem mode `0600`. This protects copied databases and casual backups;
it does not replace full-disk encryption or protect a compromised operating-system account.

## CLI contract

Primary commands:

```text
thera setup
thera chat --model <provider:model> --locale it-IT|en-US
thera telegram --model <provider:model> --locale it-IT|en-US --allowed-user-id <numeric-id>
thera auth login
thera auth status
thera auth logout
thera memory show
thera memory case
thera memory sessions
thera memory interventions
thera memory confirm <id>
thera memory correct <id> <text>
thera memory forget <id>
thera memory model status
thera memory model verify
thera memory model install
thera memory model remove
thera export [--output path]
thera delete-data
thera doctor
thera protocol validate [path]
```

`setup` downloads and verifies the local multilingual
`sentence-transformers:jinaai/jina-embeddings-v5-text-small-retrieval` model by default. The model
then runs on-device for every `chat` and `telegram` conversation. Semantic claim retrieval has no
off switch in the product CLI. `memory model status` inspects the local Hugging Face cache without
network access, `verify` checks the cached revision against Hub checksums and performs local
inference, `install` downloads or repairs the model and runs the same inference smoke test, and
`remove` deletes only that model from the shared Hugging Face cache after confirmation. Removing the
derived model files does not delete encrypted conversations or structured memory.

`thera setup` is the normal first-run path. Questionary arrow-key menus select a supported provider,
current documented model preset, locale, Telegram, and confirmation choices. ChatGPT uses device-code
OAuth; supported remote-provider API keys and the Telegram bot token use no-echo prompts and are
stored in the encrypted local store. Ollama models are discovered from its local `/api/tags`
endpoint and the standard local base URL is applied automatically. A custom PydanticAI model ID
remains available as an escape hatch. Secrets are never placed in process arguments, exports, or
plaintext configuration files. Explicit `chat` and `telegram` options remain temporary overrides.

Before asking for provider details, setup downloads and executes both document and query embeddings
with the required local multilingual model. Failure stops setup before creating the data store.
Successful setup records the exact embedding model in encrypted app state; `chat` and `telegram`
refuse missing or stale setup state. Provider and Telegram secrets are staged in memory and committed
with app defaults only after all interactive validation succeeds, so cancellation does not leave a
partially configured provider.

After `thera auth login`, omitting `--model` selects `codex:gpt-5.6-sol`. An explicit model can be
selected with `--model codex:<model-id>`. Access and refresh tokens are encrypted in the same local
store and are never included in exports.

The `codex:` provider mirrors the device-code flow and Codex Responses backend used by pi and the
open-source Codex client. It is experimental, self-hosted/personal only, and not part of the public
OpenAI API contract. OpenAI documents third-party coding harnesses, but does not document non-coding
subscription use; do not enable this provider in a SaaS or make compatibility/availability claims
without explicit terms and product review. API-key and local-model providers remain supported.

Interactive chat commands:

```text
/case
/memory
/sessions [id]
/interventions
/confirm <id>
/correct <id> <text>
/forget <id>
/end
/help
/quit
```

`/quit` only leaves the process. It does not close the therapeutic session. A later message closes
and consolidates the previous session if at least eight hours elapsed. `/end` closes it immediately.

Telegram normally reads its token and user ID from the encrypted configuration written by `setup`.
The user never needs to know or type that ID: setup validates the bot token, creates a random
single-use deep link, waits for the matching private `/start` update, displays the detected account,
and asks for confirmation before storing its ID. A phone number cannot be used to look up a Bot API
user and is neither requested nor stored.
Startup validates the token, removes any webhook without discarding pending updates, installs the
`/start`, `/help`, and `/end` menu, then long-polls text messages sequentially. The runtime ignores
groups, bots, media, and every sender except the configured numeric user ID. Telegram consent is
separate from terminal consent and explains that Telegram and any remote model provider receive
message content.

Telegram is a conversation transport, not a remote administration surface. Only `/start`, `/help`,
and `/end` are available there; memory inspection and mutation, auth, export, and deletion remain
local CLI operations. Incoming text and outgoing chunks stay below Telegram's message limit and use
plain text without a parse mode. The encrypted update offset survives restarts. A crash between model
state commit and offset persistence can still cause one update to be processed again; full durable
inbox idempotency is deferred until `ChatSession` can atomically accept an external idempotency key.

Minimal setup:

1. Create a bot with Telegram's `@BotFather`, keep its token private, and disable group joins as
   defense in depth.
2. Run `thera setup`, choose the model and locale, then paste the bot token in the hidden prompt.
3. Open the one-time `t.me` link printed by setup, press Start, and confirm the detected account.
4. Run `thera doctor`, then `thera telegram`. Only one poller may use a bot token at a time.
5. In the private bot chat, enter the exact consent command shown there.

`export` returns decrypted user-owned application state, formulation, memory items, sessions, and
messages. `delete-data` removes all of those records.

## Protocol packs

```text
protocols/<id>-v<version>/
|- manifest.yaml
|- SKILL.md
|- references/
`- skills/
   `- <therapeutic-skill>/
      |- SKILL.md
      |- agents/openai.yaml
      `- references/
```

The manifest contains the pack ID, SemVer, experimental/review status, locales, ordered therapeutic
skills, source metadata, and SHA-256 hashes for every loaded skill and reference. Changed skill or
reference files invalidate the pack. The pack contains original transdiagnostic abstractions
informed by official WHO and NICE materials. Original protocol text is licensed under the repository
license; linked sources are not copied or relicensed. It remains `experimental`; clinical review is
deferred and no clinical claims are permitted.

The current default is `therapist.transdiagnostic` v0.5.0. Its six bounded skills cover shared
formulation, psychological flexibility and emotional awareness, avoidance and behavioral change,
practical problem solving, review/maintenance, and explicit repair after misattunement. The root
skill routes each turn and permits at most one intervention skill at a time. Older packs remain
available so behavior changes are auditable.

The normal turn returns plain text capped at 1,200 characters. Durable changes use validated staged
tools, including a hypothesis offered for confirmation so a later user confirmation promotes that
exact pending memory item. Questions are optional and normally sparse; naturalness and avoidance of
interrogation are evaluated at the conversation level.

Memory tool use is intentionally sparse: at most two durable items total per turn, with no more than
one hypothesis.
Near-identical claims merge conservatively using the standard library, while differing numbers or
negation always remain distinct. An unaccepted proposed focus expires when the session closes.

On the first turn after at least seven days, the harness marks the old formulation as provisional
and requires orientation to what changed and, when relevant, the outcome of the previous experiment
before extending an old pattern to new material.

The agent recognizes misattunement semantically from the current message, history, and protocol
rather than from a fixed phrase list. The reply must acknowledge the mismatch, stop the rejected
technique, and invite one correction before further therapeutic work. Delivery preferences learned
from the repair still require exact user evidence through the memory tool.

## Engineering rules

- Use the `ponytail` skill in `full` mode for every coding, refactoring, dependency, and
  architecture task. Read its complete `SKILL.md` before making code changes. If the skill is not
  available, apply the same order manually: question speculative work, reuse existing code, prefer
  the standard library and native features, then installed dependencies, and write new abstractions
  only as a last resort. Never simplify away validation, data-loss prevention, encryption, or
  required error handling.
- Write code, documentation, prompts, schema names, and protocol content in English.
- Support Italian and English at runtime.
- Before changing code, consult the current official documentation for affected libraries.
- Work directly on `main` and push commits to `origin/main`. Do not create agent or feature branches
  or open pull requests unless the user explicitly requests that workflow.
- Prefer the standard library, native platform behavior, and installed dependencies.
- Do not add infrastructure or abstractions for deferred milestones.
- Preserve input validation, encryption, error handling that prevents data loss, and deterministic
  safety routing.
- Keep model-generated hypotheses distinct from user-confirmed facts.
- Keep model context bounded regardless of archive size.
- Update this file whenever the implementation changes any statement in it.
- Keep `README.md` concise and update it when public commands, requirements, scope, or licensing
  change.

## Acceptance checks

- A return after several simulated months retrieves relevant prior events and patterns.
- The agent does not claim a memory without archive evidence.
- Facts and hypotheses remain visibly distinct and retain provenance.
- Every direct model-written fact has an exact quote in its evidence message; unsupported facts are
  rejected before persistence.
- Natural-language corrections replace the targeted claim without leaving the contradicted version
  active, and conservative deduplication never merges different numbers or opposite negation.
- Every formulation statement resolves to an active memory ID; invented IDs and forgotten claims are
  excluded, and only explicit user wording can accept a focus.
- Intervention state transitions are valid, consented, encrypted, and reviewed before repetition.
- Offered, agreed, tried, and reviewed states for one intervention remain on one record.
- Bilingual and indirect misattunement signals produce repair before another technique.
- User correction wins over prior inference and no superseded wording returns via derived context.
- Selective forgetting and full deletion work; sensitive plaintext is absent from SQLite.
- Eight-hour segmentation, `/end`, interrupted consolidation, and session resumption preserve data.
- Context stays bounded with hundreds of sessions.
- Semantic retrieval ranks meaning-equivalent bilingual claims without weakening evidence,
  encryption, correction, or forgetting contracts, and setup fails if the model is unavailable.
- Italian and English golden conversations cover listening, continuity, gentle challenge, technique
  choice, AI transparency, and refusal to diagnose.
- An explicit matched danger disclosure bypasses the normal model response.
- Telegram rejects unauthorized/non-private input before model invocation, requires channel-specific
  consent, persists its update offset, and keeps privileged memory operations local.
- Interactive setup persists defaults and secrets encrypted, does not echo the Telegram token, and
  lets chat and Telegram start without environment configuration.

## Test strategy

The default suite is deterministic and must not require network access or provider credentials.
Pydantic Evals loads the human-readable, versioned YAML datasets in `tests/cases/`; the scope and
matrix live in `tests/TEST_PLAN.md`. Deterministic datasets execute tool, evidence, and persistence
contracts as well as auditing each therapeutic-skill file; live datasets evaluate integrated
conversation behavior. They use
synthetic people and events only; never put real user data, access tokens, or API keys in test files.

Longitudinal tests must cover retrieval after several months, encrypted persistence across process
restart, evidence provenance, fact/hypothesis separation, correction precedence, selective
forgetting, semantic reindexing and fail-closed behavior, and hard context bounds. A separate `live`
test exercises the same high-level path
against a real OpenAI model. It is skipped unless explicitly enabled:

```bash
THERA_RUN_LIVE_TESTS=1 OPENAI_API_KEY=... uv run pytest -m live
```

Live evaluation runs each case three times in a fresh encrypted database, asserts storage and
continuity contracts, and uses a Pydantic Evals `LLMJudge` rubric for therapeutic process rather than
exact wording. It covers longitudinal avoidance and alliance repair. Run it manually before releases
or after changing model integration; do not make ordinary local or CI runs depend on an external
provider.

A separate Codex-subscription memory eval exercises the configured experimental OAuth backend with
synthetic data through the production `ChatSession`: capture, explicit hypothesis confirmation,
consolidation, encrypted semantic indexing, restart, four-month retrieval, and continuity. It is
opt-in and runs once by default:

```bash
THERA_RUN_CODEX_EVALS=1 uv run pytest tests/test_live_codex_memory.py -m live
```

The deterministic semantic-memory Pydantic Evals dataset remains offline by using a fixed bilingual
embedding test model; it verifies ranking, index reuse, bounds, and absence of sensitive plaintext.

Run before handing off a change:

```bash
uv run pytest
uv run ruff check .
```

## References

- PydanticAI: https://pydantic.dev/docs/ai/overview/
- PydanticAI message history: https://pydantic.dev/docs/ai/core-concepts/message-history/
- PydanticAI structured output: https://pydantic.dev/docs/ai/core-concepts/output/
- PydanticAI embeddings: https://pydantic.dev/docs/ai/guides/embeddings/
- PydanticAI OpenAI Responses provider: https://pydantic.dev/docs/ai/models/openai/
- Pydantic Evals datasets: https://ai.pydantic.dev/evals/how-to/dataset-serialization/
- Python sqlite3: https://docs.python.org/3.12/library/sqlite3.html
- Cryptography Fernet: https://cryptography.io/en/latest/fernet/
- WHO responsible AI for mental health, 2026:
  https://www.who.int/news/item/20-03-2026-towards-responsible-ai-for-mental-health-and-well-being--experts-chart-a-way-forward
- WHO-5: https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01
- NICE NG222: https://www.nice.org.uk/guidance/ng222
- NICE NG225: https://www.nice.org.uk/guidance/ng225
- NIST AI 600-1:
  https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- OWASP Agentic Top 10:
  https://genai.owasp.org/2025/12/09/owasp-genai-security-project-releases-top-10-risks-and-mitigations-for-agentic-ai-security/
- OpenAI Codex app-server authentication:
  https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md#auth-endpoints
- OpenAI Codex for Open Source: https://developers.openai.com/community/codex-for-oss
- pi provider documentation:
  https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/providers.md
- Telegram Bot API: https://core.telegram.org/bots/api
- Telegram Bots FAQ: https://core.telegram.org/bots/faq
- OpenClaw Telegram channel:
  https://github.com/openclaw/openclaw/blob/main/docs/channels/telegram.md
