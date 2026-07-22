# Therapist

Therapist is an experimental, self-hosted AI conversation agent focused on careful listening,
longitudinal memory, collaborative case formulation, and appropriate therapeutic techniques.
It supports Italian and English through a terminal chat and a private Telegram bot.

> [!WARNING]
> Therapist is an AI, not a psychologist, psychotherapist, medical device, or emergency service.
> It does not diagnose, prescribe, or provide human monitoring. If you may be in immediate danger,
> contact local emergency services.

## Current alpha

- Natural conversation without mandatory goals or forms.
- Encrypted SQLite archive and structured memory across months or years.
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

## Memory and privacy

Messages, session summaries, structured memory, case formulation, and intervention history are
stored locally in encrypted form. Retrieval is local and bounded; the agent sends only relevant
context to the selected model provider. Remote providers and Telegram still receive the content
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
