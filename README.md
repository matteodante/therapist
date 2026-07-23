# Therapist

Therapist is an experimental, self-hosted AI conversation agent focused on careful listening,
longitudinal memory, collaborative case formulation, and appropriate therapeutic techniques.
Agent conversation supports Italian and English through a terminal chat and a private Telegram bot;
the application interface, consent notices, commands, and documentation are English.

> [!WARNING]
> Therapist is an AI, not a psychologist, psychotherapist, medical device, or emergency service.
> It does not diagnose, prescribe, or provide human monitoring. If you may be in immediate danger,
> contact local emergency services.

## Current alpha

- Natural, varied conversation guided by an internal protocol rather than a visible script, without
  mandatory questions, goals, or forms.
- Contextual agent handling of possible danger without keyword routing, diagnosis, or risk scores.
- Plain-text agent replies plus six agent-selected memory, focus, and intervention tools.
- Encrypted SQLite archive, structured memory, and local semantic retrieval across months or years.
- Visible, correctable facts, hypotheses, case formulation, sessions, and interventions.
- Complete active-session history with warning and automatic rollover at the model context limit.
- PydanticAI providers, local models, and experimental personal ChatGPT Codex OAuth.
- Git-versioned experimental therapeutic skills and evidence references.
- Deterministic tests plus longitudinal and multilingual Pydantic Evals datasets.
- Single-user CLI and allowlisted private Telegram transport with transparent memory views.

The current protocol is experimental and has not undergone clinical validation. See
[AGENTS.md](AGENTS.md) for the complete scope, architecture, memory model, and behavioral contract.
Its stable directory is `protocols/transdiagnostic/`; Git commits and tags track revisions, so the
manifest and directory name do not carry a separate SemVer version.

## Quick start

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/matteodante/therapist.git
cd therapist
uv sync
uv run thera setup
uv run thera doctor
uv run thera chat
```

Setup uses arrow-key menus, stores credentials encrypted outside the repository, and configures a
model and locale. For Telegram, create a bot with `@BotFather`; setup configures it and asks whether
to install and start its native background service. You can instead keep the listener in the
foreground:

```bash
uv run thera telegram
```

Or install and start it as a native per-user background service or task:

```bash
uv run thera telegram-service install
uv run thera telegram-service status
```

This uses a macOS LaunchAgent, Linux systemd user unit, or Windows scheduled task. The native
definition contains only command paths and reads tokens and provider credentials from the existing
encrypted store. Use `telegram-service restart` after configuration changes and
`telegram-service uninstall` to stop the process and remove its background definition.

Run `uv run thera --help` for all commands. Inside chat, `/help` lists memory, session, correction,
forgetting, and session-closing commands.

Conversation context uses the selected model's limit up to an application cap of 128,000 tokens,
always reserving 10% for model output. Use `--context-window-tokens` on `chat` or `telegram` to set a
lower known limit, down to 16,000.

Inside Telegram, `/status`, `/case`, `/memory`, `/sessions`, `/interventions`, and `/privacy` expose
the active session, evidence-linked formulation, paginated structured memory, intervention history,
and data flow. Durable memory, focus, or intervention changes are disclosed after the reply that
commits them. Sensitive mutations, export, deletion, authentication, internal prompts, secrets, and
private model reasoning remain local or hidden.

Private semantic retrieval is enabled by default using PydanticAI embeddings and an encrypted,
rebuildable local index:

```bash
uv run thera chat
```

During `thera setup`, the pinned Apache-2.0 Qwen3 multilingual model downloads once from Hugging Face
and both query and document embeddings are verified before the encrypted data store is created.
Provider and Telegram configuration is saved only after the interactive flow succeeds. It then runs
on-device. Semantic retrieval for claims, interventions, and historical excerpts is mandatory:
incomplete or stale setup state and unavailable local embeddings stop conversation with setup
guidance instead of silently using weaker lexical-only retrieval.

Inspect, verify, repair, or remove only the pinned local model revision with:

```bash
uv run thera memory model status
uv run thera memory model verify
uv run thera memory model install
uv run thera memory model remove
```

## Memory and privacy

Messages, session summaries, structured memory, case formulation, and intervention history are
stored locally in encrypted form. Retrieval and its semantic index are local and bounded; the index
is derived from claims, active interventions, and candidate user messages and is not a second source
of truth. The agent can request an additional bounded local lookup when the initial context is
insufficient. The remaining five tools stage validated memory observations, corrections, hypothesis
confirmations, focus changes, or one intervention update. The transcript and staged changes are
committed atomically only after a successful final reply. Tool exchanges are not retained:
conversation history contains only the canonical user message and plain-text assistant reply.
Slash commands, their displayed output, tool traces, and context lifecycle notices are never stored
as conversation turns or returned to the conversation model. There is no intra-session compaction:
complete canonical turns remain available until a warning near the effective context limit, followed
by consolidation and a fresh session before the next message would exceed it. End-of-session
consolidation separately uses a structured `SessionReflection`; conversation turns do not return
process-stage or selected-skill fields. The agent sends only relevant context to the selected model
provider. Remote providers and Telegram receive the content needed to answer or deliver messages.
Use `thera export` to inspect your data and `thera delete-data` to remove it.

## Development

```bash
uv sync --all-groups --extra dev
uv run ruff check src tests
uv run pytest -q
uv run thera protocol validate
uv build
```

Real-provider tests are opt-in and never run in CI. Never put real conversations, credentials, or
other sensitive personal data in tests or issues. Test code and fixtures are written in English
unless a case explicitly verifies localized behavior or multilingual retrieval.

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes. Report vulnerabilities privately
according to [SECURITY.md](SECURITY.md).

## License

Original code and project content are licensed under
[AGPL-3.0-or-later](LICENSE). Linked WHO, NICE, and other third-party materials remain under their
respective owners' terms and are not copied into this repository.
