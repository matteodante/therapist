# Contributing

Therapist is an experimental mental-health-adjacent project. Small, well-tested changes are
preferred. Open an issue before major behavioral, protocol, dependency, or architecture changes.

## Development

Use Python 3.12 or newer and `uv`:

```bash
uv sync --all-groups --extra dev
uv run ruff check src tests
uv run pytest -q
uv run thera protocol validate
uv build
```

Code, documentation, prompts, protocol content, tests, and test fixtures are written in English.
Use another language in tests only when the case explicitly verifies localization or multilingual
behavior. Agent conversation should preserve Italian and English support; static application
interfaces remain English. Never commit credentials, real conversations, or other sensitive data.

Protocol changes must update their manifest, hashes, references, and evaluation cases. Use original
summaries and abstractions; do not copy therapeutic source material unless its license explicitly
permits this repository's use.

By contributing, you agree that your contribution is licensed under AGPL-3.0-or-later. Be
respectful, specific, and focused on the work in issues and reviews.
