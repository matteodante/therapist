# Therapist

Therapist is an experimental, self-hosted AI conversation agent focused on careful listening,
longitudinal memory, collaborative case formulation, and appropriate therapeutic techniques.
It supports Italian and English through a terminal chat and a private Telegram bot.

> [!WARNING]
> Therapist is an AI, not a psychologist, psychotherapist, medical device, or emergency service.
> It does not diagnose, prescribe, or provide human monitoring. If you may be in immediate danger,
> contact local emergency services.

## Current alpha

- Natural, varied conversation guided by an internal protocol rather than a visible script, without
  mandatory questions, goals, or forms.
- Encrypted SQLite archive, structured memory, and local semantic retrieval across months or years.
- Visible, correctable facts, hypotheses, case formulation, sessions, and interventions.
- PydanticAI providers, local models, and experimental personal ChatGPT Codex OAuth.
- Versioned experimental therapeutic skills and evidence references.
- Deterministic tests and bilingual Pydantic Evals datasets.
- Single-user CLI and allowlisted private Telegram transport.

The current protocol is experimental and has not undergone clinical validation. See
[AGENTS.md](AGENTS.md) for the complete scope, architecture, memory model, and behavioral contract.

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
model and locale. For Telegram, create a bot with `@BotFather`, configure it during setup, then keep
the listener running:

```bash
uv run thera telegram
```

Run `uv run thera --help` for all commands. Inside chat, `/help` lists memory, session, correction,
forgetting, and session-closing commands.

Private semantic retrieval is enabled by default using PydanticAI embeddings and an encrypted,
rebuildable local index:

```bash
uv run thera chat
```

During `thera setup`, the multilingual model downloads once from Hugging Face and both query and
document embeddings are verified before the encrypted data store is created. Provider and Telegram
configuration is saved only after the interactive flow succeeds. It then runs on-device. Semantic
claim retrieval is mandatory: incomplete or stale setup state and unavailable local embeddings stop
conversation with setup guidance instead of silently using weaker lexical-only retrieval.

## Memory and privacy

Messages, session summaries, structured memory, case formulation, and intervention history are
stored locally in encrypted form. Retrieval and its semantic index are local and bounded;
the index is derived from evidence-linked claims and is not a second source of truth. The agent
sends only relevant context to the selected model provider. Remote providers and Telegram receive the content
needed to answer or deliver messages. Use `thera export` to inspect your data and
`thera delete-data` to remove it.

## Development

```bash
uv sync --all-groups --extra dev
uv run ruff check src tests
uv run pytest -q
uv run thera protocol validate
uv build
```

Real-provider tests are opt-in and never run in CI. Never put real conversations, credentials, or
other sensitive personal data in tests or issues.

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes. Report vulnerabilities privately
according to [SECURITY.md](SECURITY.md).

## License

Original code and project content are licensed under
[AGPL-3.0-or-later](LICENSE). Linked WHO, NICE, and other third-party materials remain under their
respective owners' terms and are not copied into this repository.
