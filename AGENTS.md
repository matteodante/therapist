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
- keeps behavioral instructions and source references in Git-versioned protocol packs;
- lets the user inspect, confirm, correct, forget, export, and delete memory;
- records offered, agreed, tried, stopped, and untried interventions for later review;
- accepts the same therapeutic conversation through a private, allowlisted Telegram bot;
- remains small enough for one maintainer to understand.

Included in this milestone:

- interactive terminal chat;
- private text-only Telegram chat using long polling and the standard Bot API;
- native per-user Telegram background installation for macOS launchd, Linux systemd, and Windows
  Task Scheduler;
- one PydanticAI conversational agent and one end-of-session consolidation pass;
- device-code ChatGPT OAuth, encrypted token storage, and automatic refresh for the experimental
  `codex:` provider;
- encrypted SQLite archive and layered longitudinal memory;
- automatic session boundaries after eight hours of inactivity and explicit `/end`;
- an experimental bilingual transdiagnostic behavior pack;
- contextual agent instructions for possible danger, including Italian/EU and US resources;
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
and contextual agent instructions for possible danger and emergency resources. These are not a
validated clinical safety system.

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
CLI or private Telegram -> Git-versioned experimental behavior and safety instructions
  |
  v
PydanticAI tool loop + plain-text reply -> local model or configured remote provider
  |
  v
Encrypted SQLite archive + structured longitudinal memory
```

Use one PydanticAI agent run per conversation turn. The agent returns the visible reply as `str` and may
call six bounded function tools: `search_memory`, `record_memory`, `correct_memory`,
`confirm_hypotheses`, `set_focus`, and `record_intervention`. The first is an optional read-only
longitudinal lookup; the other five validate and stage actions without mutating SQLite during the
model run. After a valid final reply, the transcript and all staged actions are committed in one
transaction; failure leaves both unchanged. The successful PydanticAI message sequence is retained
in encrypted model history, including paired function-tool inputs and outputs but excluding repeated
internal instructions and provider thinking, and those tool exchanges are rendered before the final
reply in both CLI and Telegram. Slash commands such as `/start`,
`/status`, and `/quit`, their rendered output, and transport-level notices remain excluded from the
conversation archive and model history.

Conversation transports receive cumulative reply snapshots and tool input/output events from the
complete PydanticAI event stream. Drafts may contain an output attempt that is later rejected; the
next attempt replaces it, and only the validated final output is committed. Provider thinking is
never emitted. CLI renders drafts in Textual and Telegram uses ephemeral rich-message drafts.

A conversation run permits at most eight model requests, six successful tool calls, two validation
retries for each invalid tool call, and two output retries within that global budget. All
model-written strings and collections have size limits. Accepted
focus, confirmed hypotheses, and agreed or updated interventions require exact supporting text from
the current user message. The IDs of the last explicitly offered hypothesis and active intervention
remain pending so confirmation, agreement, and outcome update the original records instead of
creating copies. Provider transport retries remain a separate concern.

When a session closes, use one additional model call with the structured `SessionReflection` output
to summarize the episode and link existing claims into the case formulation. Consolidation allows
two output retries and at most three model requests. It cannot create a confirmed claim. If it fails,
preserve the transcript, record a content-free error class, and leave the previous formulation
intact. Both agent runs use PydanticAI's complete synchronous API with an event stream handler so the
experimental ChatGPT Codex backend can require `stream=true`; conversation transports stream
cumulative Markdown snapshots while preserving the complete tool graph, then render the validated
final reply. Consolidation consumes its stream without exposing a draft.

Consolidation preserves valid formulation links when the model omits them and removes a link only
through an explicit `formulation_unlinks` entry. Existing evidence is retained before new links when
a field reaches its five-claim bound, so omission or overflow cannot silently evict history.

Memory retrieval uses local hybrid ranking over validated claims, active interventions, and up to
1,000 recent user archive messages by default: lexical overlap plus semantic similarity through
PydanticAI `Embedder`, with recency as a tie-breaker. The semantic index is an encrypted, derived
SQLite cache keyed by entity type, entity ID, exact model revision, and keyed content hash; it is
rebuilt after content or model changes and its affected rows are deleted on correction or
forgetting. SQLite/Fernet remains the source of truth.
Semantic retrieval is a required memory capability: setup downloads and verifies the local model,
and conversation fails closed with setup guidance when embeddings are unavailable rather than
silently switching to lexical-only ranking. Historical excerpts use the same hybrid ranking and a
minimum semantic relevance threshold; lexical tokenization adds standard-library character bigrams
for Chinese, Japanese, and Thai text without spaces. Context is reduced by complete structured items
and serialized only as valid JSON; model history and consolidation retain complete turns instead of
slicing messages mid-run. There is no intra-session compaction. Successful-run history grows until a
conservative estimate reaches 80% of the input budget, when the user receives one warning. Before a
later user turn would exceed that budget, the old session is consolidated with `context_limit` as
its end reason and the pending message starts a new session. The effective context window is the
configured model limit capped at 128,000 tokens, with 10% always reserved for model output.

## Memory model

Memory is layered so that "remember everything" does not mean sending the entire archive to the
model on every turn.

- `Message`: complete encrypted user/assistant archive retained until deletion.
- `Session`: time- or context-bounded episode with summary, themes, interventions, user response,
  open questions, and an explicit end reason.
- `MemoryItem`: a durable fact, preference, consequential event, pattern, or hypothesis with
  provenance and timestamps; a turn may write at most two.
- `CaseFormulation`: an evidence map that derives concerns, triggers, thoughts, behavior, coping,
  relationships, course, functioning, explanatory model, preferences, maintaining factors,
  strengths, hypotheses, and focus from active memory claim IDs.
- `InterventionRecord`: one offered or agreed technique with consent state, linked claims,
  prediction, outcome, user appraisal, and follow-up information. It is not a goal.
- `WorkingContext`: formulation, bounded confirmed memory, unresolved hypotheses, the latest three
  completed sessions, at most five active interventions, and five historical excerpts.
- `SemanticIndex`: encrypted vectors for active memory items, active interventions, and bounded
  candidate user messages. It is derived, excluded from export, safe to discard, and never
  establishes truth or provenance.

Memory states:

- `user_confirmed`: directly stated or explicitly confirmed by the user;
- `agent_hypothesis`: an interpretation that must remain tentative;
- `user_corrected`: a user correction that overrides older inferences;
- `archived`: excluded from future context while retained in the user's export until full deletion.

The complete archive is retained until the user deletes it. Corrections and forgotten items must be
removed from derived formulation and summaries and suppressed from future retrieval. Current-session
model history retains every complete successful run, including tool exchanges, until the context
boundary; long-term continuity across the resulting sessions comes from structured context and
relevant excerpts.
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

The normal end-user installation is a copy-paste bootstrap from GitHub: `install.sh` supports macOS
and Linux, while `install.ps1` supports Windows PowerShell. Both download the current `main` source
archive, install a pinned uv bootstrap only when uv is absent, use uv-managed Python 3.12 to install
`therapist-cli` as an isolated user tool, expose `thera` on the user's PATH, run interactive
`thera setup`, and then run `thera doctor`. They require no administrator privileges, existing
Python, or Git checkout. Re-running the same installer updates the alpha without deleting encrypted
application state or the shared Hugging Face model cache. `uv tool uninstall therapist-cli` removes
the application command but intentionally leaves user data in place.

Primary commands:

```text
thera setup
thera chat [--plain] --model <provider:model> --locale it-IT|en-US --context-window-tokens <16000..128000>
thera telegram --model <provider:model> --locale it-IT|en-US --allowed-user-id <numeric-id> --context-window-tokens <16000..128000>
thera telegram-service install
thera telegram-service status
thera telegram-service restart
thera telegram-service uninstall
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

`thera chat` uses a full-screen Textual interface in an interactive terminal. It restores the latest
50 user/assistant turns from the active session, renders assistant Rich Markdown, displays live tool
events, and disables input while one sequential turn is running. `--plain` forces the line-oriented
streaming interface; non-interactive stdin or stdout selects it automatically. The TUI never loads
more than 50 historical turns and does not replay old tool traces.

`setup` downloads and verifies the local multilingual Apache-2.0
`sentence-transformers:Qwen/Qwen3-Embedding-0.6B` model at the repository-pinned revision. The model
then runs on-device for every `chat` and `telegram` conversation. Semantic retrieval has no off
switch in the product CLI. `memory model status` inspects the exact revision in the local Hugging
Face cache without network access, `verify` checks it against Hub checksums and performs local
inference, `install` downloads or repairs it, runs the same inference smoke test, and updates an
existing encrypted app configuration, and `remove` deletes only that revision from the shared cache
after confirmation. Removing the derived model files does not delete encrypted conversations or
structured memory.

Setup stores a conservative context-window limit for the selected conversation model. Known remote
presets use their documented limit subject to the application-wide 128,000-token cap. Ollama models
are inspected through `/api/show`; an unknown or custom model defaults to that cap and can be
overridden downward per process with `--context-window-tokens`. An override can never exceed the
detected model limit. During setup, a validated text prompt displays the current saved value and the
available range and lets the user replace it. Models below the 16,000-token supported minimum are
rejected.

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
partially configured provider. When Telegram is configured, setup asks whether to install and start
its native per-user background service or task after the encrypted configuration is committed.

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
When the active history approaches its context boundary, a warning is printed without archiving it.
The next over-budget message closes and consolidates the old session, starts a new one, and is
processed there. Commands, their output, and these lifecycle notices never enter conversation
history. Agent function-tool calls are not commands: their input and output are displayed and saved
in encrypted model history.

Telegram normally reads its token and user ID from the encrypted configuration written by `setup`.
The user never needs to know or type that ID: setup validates the bot token, creates a random
single-use deep link, waits for the matching private `/start` update, displays the detected account,
and asks for confirmation before storing its ID. A phone number cannot be used to look up a Bot API
user and is neither requested nor stored.
Startup validates the token, removes any webhook without discarding pending updates, installs the
allowlisted chat's English command menu and transparent bot description, then long-polls text
messages sequentially. The runtime ignores groups, bots, and every sender except the configured
numeric user ID. Unsupported media receives a clear text-only notice without model invocation or
storage. Telegram consent is separate from terminal consent and explains that Telegram receives
messages, replies, and any local data the user requests to inspect there, while any remote model
provider receives message content and selected context.

Telegram is a conversation and read-only transparency surface, not a remote administration surface.
`/status`, `/case`, `/memory [page]`, `/sessions [page|id]`, `/interventions [page]`, and `/privacy`
show the agent identity, active session, bounded paginated structured state, evidence links, data
flow, and limitations. `/start`, `/help`, and `/end` manage consent, guidance, and the conversational
session. After each normal reply, the bot reports any durable memory, focus, or intervention changes
committed for that turn. Correcting or forgetting memory, auth, export, and deletion remain local CLI
operations. Command messages, rendered command output, context warnings, and rollover notices are
transport-only and are not archived or sent back to the conversation model. Internal prompts,
secrets, and private model reasoning are never exposed. Function-tool inputs and outputs are sent as
separate messages before the final reply and remain in encrypted model history. Reply generation
uses a random non-zero `sendRichMessageDraft` ID, updates the ephemeral Rich Markdown draft at most
four times per second, and persists the validated output with `sendRichMessage`. Unsupported or
rejected rich formatting falls back to plain text. Durable-change notices remain separate plain-text
messages. Incoming text and outgoing content stay below Telegram's limits. The encrypted update offset
survives restarts. A crash between model state commit and offset persistence can still cause one
update to be processed again; full durable inbox idempotency is deferred until `ChatSession` can
atomically accept an external idempotency key.

`thera telegram-service install` validates the saved configuration and starts the listener without
putting secrets in process arguments. It writes a mode-`0600` LaunchAgent in
`~/Library/LaunchAgents` on macOS, a mode-`0600` user unit in `~/.config/systemd/user` on Linux, or a
limited-privilege per-user scheduled task on Windows. The listener starts with the user's login;
Linux operation beyond logout depends on the host's user manager/lingering policy. `status`,
`restart`, and `uninstall` inspect, restart, or stop the process and remove only this native
definition. macOS operational output is written to the application data directory's
`telegram-service.log`; Linux output is available through the user journal.

Minimal setup:

1. Create a bot with Telegram's `@BotFather`, keep its token private, and disable group joins as
   defense in depth.
2. Run `thera setup`, choose the model and locale, then paste the bot token in the hidden prompt.
3. Open the one-time `t.me` link printed by setup, press Start, and confirm the detected account.
4. Choose whether setup should install the background service, or run `thera telegram` manually.
   Only one poller may use a bot token at a time.
5. Run `thera doctor`, then enter the exact consent command shown in the private bot chat.

`export` returns decrypted user-owned application state, formulation, memory items, sessions, and
messages. `delete-data` removes all of those records.

## Protocol packs

```text
protocols/<id>/
|- manifest.yaml
|- SKILL.md
|- references/
`- skills/
   `- <therapeutic-skill>/
      |- SKILL.md
      |- agents/openai.yaml
      `- references/
```

The manifest contains the pack ID, experimental/review status, locales, ordered therapeutic skills,
source metadata, and SHA-256 hashes for every loaded skill and reference. Changed skill or reference
files invalidate the pack. Protocol history and releases are identified by Git commits and tags
rather than duplicated SemVer directories or a manifest version. Keep one directory per genuinely
different protocol; do not copy a directory merely to preserve an older revision.

The canonical protocol remains under `protocols/`. The wheel build copies the default pack into the
installed `therapist` package so a user-tool installation is self-contained; source checkouts fall
back to the canonical repository path.

The pack contains original transdiagnostic abstractions informed by official WHO and NICE materials.
Original protocol text is licensed under the repository license; linked sources are not copied or
relicensed. It remains `experimental`; clinical review is deferred and no clinical claims are
permitted.

The current default is `therapist.transdiagnostic`. Its six bounded skills cover shared
formulation, psychological flexibility and emotional awareness, avoidance and behavioral change,
practical problem solving, review/maintenance, and explicit repair after misattunement. The root
skill routes each turn and permits at most one intervention skill at a time.

Each turn returns concise GitHub-compatible Markdown capped at 1,200 characters, without raw HTML,
images, or embedded media. Durable changes use validated staged tools, including a hypothesis
offered for confirmation so a later user confirmation promotes that exact pending memory item.
Questions are optional and normally sparse; naturalness and avoidance of interrogation are evaluated
at the conversation level. The turn has no `process_stage`,
`selected_skill`, or other model-written process classifier; the prompt supplies the full protocol
and the agent chooses conversational behavior and tools from meaning and context.

Memory tool use is intentionally sparse: at most two durable items total per turn, with no more than
one hypothesis. A model-written pattern remains tentative by default. A directly stated user pattern
may be stored as confirmed only when its content and evidence are the same exact quote from the
current message.
Near-identical claims merge conservatively using the standard library, while differing numbers or
negation always remain distinct. An unaccepted proposed focus expires when the session closes.

On the first turn after at least seven days, the harness marks the old formulation as provisional
and requires orientation to what changed and, when relevant, the outcome of the previous experiment
before extending an old pattern to new material.

The agent recognizes misattunement semantically from the current message, history, and protocol
rather than from a fixed phrase list. The reply must acknowledge the mismatch, stop the rejected
technique, and invite one correction before further therapeutic work. Delivery preferences learned
from the repair still require exact user evidence through the memory tool.

Relational safety is part of the protocol: the agent must not encourage exclusivity, imply human
feelings, or use remembered vulnerability to drive engagement. It follows user-defined functioning
and unwanted effects over time, stops an intervention before adapting it when harm is reported, and
plainly distinguishes AI-supported conversation or self-help from diagnosis and clinical treatment.

## Engineering rules

- Use the `ponytail` skill in `full` mode for every coding, refactoring, dependency, and
  architecture task. Read its complete `SKILL.md` before making code changes. If the skill is not
  available, apply the same order manually: question speculative work, reuse existing code, prefer
  the standard library and native features, then installed dependencies, and write new abstractions
  only as a last resort. Never simplify away validation, data-loss prevention, encryption, or
  required error handling.
- Write code, documentation, prompts, schema names, protocol content, tests, and test fixtures in
  English. Use another language in a test only when that language is required to verify localized
  behavior or multilingual retrieval.
- Support Italian and English at runtime.
- Before changing code, consult the current official documentation for affected libraries.
- Work directly on `main` and push commits to `origin/main`. Do not create agent or feature branches
  or open pull requests unless the user explicitly requests that workflow.
- Prefer the standard library, native platform behavior, and installed dependencies.
- Do not add infrastructure or abstractions for deferred milestones.
- Preserve input validation, encryption, error handling that prevents data loss, and contextual
  safety instructions.
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
- Exclusive reliance on the agent is met with warmth, preserved autonomy, and support for realistic
  human connection rather than reciprocated dependency or abrupt rejection.
- Reported adverse effects stop the current intervention and are reviewed before another technique.
- User correction wins over prior inference and no superseded wording returns via derived context.
- Selective forgetting and full deletion work; sensitive plaintext is absent from SQLite.
- Eight-hour segmentation, `/end`, interrupted consolidation, and session resumption preserve data.
- Context stays bounded with hundreds of sessions; history is not truncated after an arbitrary turn
  count, emits one warning near capacity, and rolls over before exceeding the per-model limit capped
  at 128,000 tokens while preserving a 10% output reserve.
- Slash commands, rendered command output, and lifecycle notices never enter the archive or model
  history.
- CLI chat opens a responsive Textual interface on a TTY, restores only the latest 50 active-session
  turns, renders Markdown and live tool events, and retains a streaming `--plain` fallback.
- Rejected output attempts may appear only as replaceable transport drafts; only the validated final
  reply is committed. Telegram uses one throttled non-zero rich draft ID and a persistent rich final
  message, with safe plain-text fallback.
- Function-tool inputs and outputs are visible in CLI and Telegram, persist atomically with the
  successful turn, appear in user export without internal prompts or reasoning, and return in future
  model history.
- Semantic retrieval ranks meaning-equivalent claims, archive excerpts, and interventions across the
  evaluated Latin, Arabic, Devanagari, Han, Japanese, Thai, and Cyrillic scripts without weakening
  evidence, encryption, correction, or forgetting contracts; setup fails if the model is unavailable.
- English golden conversations cover listening, continuity, gentle challenge, technique choice, AI
  transparency, and refusal to diagnose; dedicated multilingual tests cover non-English behavior.
- Possible danger is evaluated from meaning and context rather than keywords; ambiguous situations
  receive a direct safety clarification, while possible immediate danger receives an urgent,
  localized response without diagnosis, scoring, or claims of monitoring.
- Telegram rejects unauthorized/non-private input before model invocation, requires channel-specific
  consent, persists its update offset, exposes read-only state with evidence and pagination, reports
  durable turn changes, and keeps privileged memory operations local.
- Telegram background installation uses the native per-user service or task manager, keeps secrets
  out of process arguments and native definitions, and supports status, restart, and clean removal
  on macOS, Linux, and Windows.
- Interactive setup persists defaults and secrets encrypted, does not echo the Telegram token, and
  lets chat and Telegram start without environment configuration. It displays and permits replacing
  the saved context limit without exceeding the selected model or application cap.

## Test strategy

The default suite is deterministic and must not require network access or provider credentials.
Pydantic Evals loads the human-readable, versioned YAML datasets in `tests/cases/`; the scope and
matrix live in `tests/TEST_PLAN.md`. Deterministic datasets execute tool, evidence, and persistence
contracts as well as auditing each therapeutic-skill file; live datasets evaluate integrated
conversation behavior. They use
synthetic people and events only; never put real user data, access tokens, or API keys in test files.
Test code and fixtures are English by default. Non-English text is limited to cases that explicitly
verify localized behavior or multilingual retrieval.

Longitudinal tests must cover retrieval after several months, encrypted persistence across process
restart, evidence provenance, fact/hypothesis separation, correction precedence, selective
forgetting, semantic reindexing and fail-closed behavior, complete active-session history beyond ten
turns, warning and automatic rollover at hard context bounds, and command/output separation. A
separate `live`
test exercises the same high-level path
against a real OpenAI model. It is skipped unless explicitly enabled:

```bash
THERA_RUN_LIVE_TESTS=1 OPENAI_API_KEY=... uv run pytest -m live
```

Live evaluation runs each case three times in a fresh encrypted database, asserts storage and
continuity contracts, and uses a Pydantic Evals `LLMJudge` rubric for therapeutic process rather than
exact wording. It covers longitudinal avoidance, alliance repair, relational dependency, and adverse
intervention effects. Offline workflow evals also assert the available tool surface, selected tool
path, persistence result, and absence of state changes when no tool is needed. Run live evals
manually before releases or after changing model integration; do not make ordinary local or CI runs
depend on an external provider.

Deterministic runtime-contract tests additionally verify that staged tool actions survive output
retry but never persist after a failed run, successful history retains paired tool exchanges, and the
per-turn tool-call budget is enforced before commit.

A separate Codex-subscription memory eval exercises the configured experimental OAuth backend with
synthetic data through the production `ChatSession`: capture, explicit hypothesis confirmation,
visible and persisted tool input/output, transcript and export integrity, provider-thinking
exclusion, consolidation summary, encrypted semantic indexing, restart, four-month retrieval, and
continuity. It is opt-in and runs once by default:

```bash
THERA_RUN_CODEX_EVALS=1 uv run pytest tests/test_live_codex_memory.py -m live
```

The deterministic semantic-memory Pydantic Evals dataset remains offline by using a fixed bilingual
embedding test model; it verifies ranking, index reuse, bounds, and absence of sensitive plaintext.

An opt-in local-model Pydantic Evals dataset verifies claim, archive-excerpt, and intervention
retrieval across Italian, English, Spanish, French, German, Portuguese, Arabic, Hindi, Chinese,
Japanese, Thai, and Ukrainian paths. It runs sequentially because Pydantic Evals otherwise executes
all cases concurrently and can exhaust RAM with a local model:

```bash
THERA_RUN_MULTILINGUAL_EMBEDDING_EVALS=1 \
  uv run pytest tests/test_multilingual_embedding_eval.py -m live
```

`THERA_MULTILINGUAL_EVAL_OFFSET` and `THERA_MULTILINGUAL_EVAL_LIMIT` can split the matrix into
resource-bounded batches without changing the dataset.

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
- Pydantic Evals concurrency: https://pydantic.dev/docs/ai/evals/how-to/concurrency/
- PydanticAI OpenAI Responses provider: https://pydantic.dev/docs/ai/models/openai/
- Pydantic Evals datasets: https://ai.pydantic.dev/evals/how-to/dataset-serialization/
- Python sqlite3: https://docs.python.org/3.12/library/sqlite3.html
- Cryptography Fernet: https://cryptography.io/en/latest/fernet/
- Qwen3-Embedding-0.6B: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
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
- Apple launchd jobs:
  https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
- systemd user services: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- Windows Task Scheduler:
  https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks
- OpenClaw Telegram channel:
  https://github.com/openclaw/openclaw/blob/main/docs/channels/telegram.md
