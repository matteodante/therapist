# Therapist project guide

This file is the canonical source of truth for the project's purpose, scope, architecture, and
working rules. Keep it updated in the same change whenever behavior, commands, storage, scope,
architecture, dependencies, or milestones change. Do not create a `README.md`; public-facing
documentation can be generated from this file when the project is prepared for release.

## Project idea

Therapist is an experimental, self-hosted AI conversation agent that reproduces the useful
process qualities of a therapist: careful listening, longitudinal continuity, collaborative case
formulation, pattern recognition, gentle challenge, and selection of an appropriate next step.

It remains explicitly an AI. It must not claim to be a psychologist or psychotherapist, diagnose,
prescribe, promise recovery, present itself as an emergency service, or imply human monitoring.

The long-term product may support both self-hosted and SaaS distribution. The current milestone is
deliberately smaller: make the single-user conversation and long-term memory work well through the
local CLI and one private Telegram transport before building broader infrastructure.

The repository is intended to become open source. The exact code and content licenses remain TBD
until the dedicated pre-release review.

## Current scope

Build a small bilingual, single-user agent that:

- holds a warm, active, natural conversation in Italian or English;
- identifies user-stated difficulties and recurring patterns without requiring predefined goals;
- builds a visible, correctable, evidence-linked case formulation;
- remembers relevant context across weeks, months, and years;
- keeps the complete archive and structured memory encrypted on the local machine;
- works with local or remote model providers through PydanticAI;
- optionally uses a personal ChatGPT Plus/Pro Codex subscription through experimental OAuth;
- versions behavioral instructions and source references in a protocol pack;
- lets the user inspect, confirm, correct, forget, export, and delete memory;
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
- embeddings, vector databases, knowledge graphs, and multi-agent orchestration;
- final code/content licensing, dual licensing, a CLA, and release packaging;
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
- understand and reflect before suggesting an action;
- ask brief, concrete questions and avoid interrogation;
- identify recurring themes and inconsistencies with a gentle, collaborative tone;
- label interpretations as hypotheses until the user confirms them;
- ask permission before exercises;
- do not force a goal, worksheet, or technique onto every exchange;
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
PydanticAI structured response -> local model or configured remote provider
  |
  v
Encrypted SQLite archive + structured longitudinal memory
```

Use one conversational model call per normal turn. Its structured result contains the visible reply,
candidate observations, and an optional current focus. When a session closes, use one additional
structured model call to summarize the episode and revise the case formulation. If consolidation
fails, preserve the transcript and leave the previous formulation intact.

Structured turn and consolidation outputs allow two correction retries. This absorbs occasional
schema or conversational-contract violations while retaining strict validation; provider transport
retries remain a separate concern.

No network call is needed for memory retrieval. Relevant historical excerpts are selected locally
using dates, structured types, and standard-library lexical matching after decryption.

## Memory model

Memory is layered so that "remember everything" does not mean sending the entire archive to the
model on every turn.

- `Message`: complete encrypted user/assistant archive retained until deletion.
- `Session`: time-bounded episode with summary, themes, interventions, user response, and open
  questions.
- `MemoryItem`: a fact, preference, event, pattern, or hypothesis with provenance and timestamps.
- `CaseFormulation`: current understanding of concerns, triggers, thoughts, behavior, coping,
  relationships, maintaining factors, strengths, hypotheses, and current focus.
- `WorkingContext`: formulation, bounded confirmed memory, unresolved hypotheses, the latest three
  completed sessions, and at most five locally retrieved historical excerpts.

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

SQLite comes from the Python standard library. Sensitive payloads are encrypted with Fernet using a
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
thera memory confirm <id>
thera memory correct <id> <text>
thera memory forget <id>
thera export [--output path]
thera delete-data
thera doctor
thera protocol validate [path]
```

`thera setup` is the normal first-run path. It interactively stores the default model, locale,
Telegram bot token, and numeric Telegram user ID in the existing encrypted local store. Secret input
uses the terminal's no-echo password prompt. The token is never placed in process arguments, exports,
or plaintext configuration files. Explicit `chat` and `telegram` options remain temporary overrides.
When a `codex:` model is selected without an existing credential, setup offers to run the existing
ChatGPT device-code login immediately.

After `thera auth login`, omitting `--model` selects `codex:gpt-5.5`. An explicit model can be
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
2. Obtain the intended account's stable numeric Telegram user ID; do not authorize by username.
3. Run `thera setup` and enter the model, locale, bot token, and allowed user ID when prompted.
4. Run `thera doctor`, then `thera telegram`. Only one poller may use a bot token at a time.
5. In the private bot chat, use `/start` and enter the exact consent command shown there.

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
informed by official WHO and NICE materials. It remains `experimental`; content licensing and
clinical review are deferred until before public distribution or clinical claims.

The current default is `therapist.transdiagnostic` v0.3.0. Its five bounded skills cover shared
formulation, psychological flexibility and emotional awareness, avoidance and behavioral change,
practical problem solving, and review/maintenance. The root skill routes each turn and permits at
most one intervention skill at a time. Older packs remain available so behavior changes are
auditable.

The structured turn output keeps the visible reply to 1,200 characters and at most one question,
records a hypothesis offered for confirmation separately, and lets a later explicit user
confirmation promote that exact memory item.

On the first turn after at least seven days, the harness marks the old formulation as provisional
and requires orientation to what changed and, when relevant, the outcome of the previous experiment
before extending an old pattern to new material.

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
- Prefer the standard library, native platform behavior, and installed dependencies.
- Do not add infrastructure or abstractions for deferred milestones.
- Preserve input validation, encryption, error handling that prevents data loss, and deterministic
  safety routing.
- Keep model-generated hypotheses distinct from user-confirmed facts.
- Keep model context bounded regardless of archive size.
- Update this file whenever the implementation changes any statement in it.

## Acceptance checks

- A return after several simulated months retrieves relevant prior events and patterns.
- The agent does not claim a memory without archive evidence.
- Facts and hypotheses remain visibly distinct and retain provenance.
- User correction wins over prior inference and no superseded wording returns via derived context.
- Selective forgetting and full deletion work; sensitive plaintext is absent from SQLite.
- Eight-hour segmentation, `/end`, interrupted consolidation, and session resumption preserve data.
- Context stays bounded with hundreds of sessions.
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
matrix live in `tests/TEST_PLAN.md`. The deterministic datasets audit longitudinal memory and every
therapeutic-skill contract; the live dataset evaluates integrated conversation behavior. They use
synthetic people and events only; never put real user data, access tokens, or API keys in test files.

Longitudinal tests must cover retrieval after several months, encrypted persistence across process
restart, evidence provenance, fact/hypothesis separation, correction precedence, selective
forgetting, and hard context bounds. A separate `live` test exercises the same high-level path
against a real OpenAI model. It is skipped unless explicitly enabled:

```bash
THERA_RUN_LIVE_TESTS=1 OPENAI_API_KEY=... uv run pytest -m live
```

The live case asserts storage and continuity contracts and uses a Pydantic Evals `LLMJudge` rubric
for therapeutic process rather than exact wording. Run it manually before releases or after changing
model integration; do not make ordinary local or CI runs depend on an external provider.

Run before handing off a change:

```bash
uv run pytest
uv run ruff check .
```

## References

- PydanticAI: https://pydantic.dev/docs/ai/overview/
- PydanticAI message history: https://pydantic.dev/docs/ai/core-concepts/message-history/
- PydanticAI structured output: https://pydantic.dev/docs/ai/core-concepts/output/
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
