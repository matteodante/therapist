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

Code, documentation, prompts, and protocol content are written in English. Runtime behavior and
tests should preserve Italian and English support. Never commit credentials, real conversations, or
other sensitive personal data.

Protocol changes must update their manifest, hashes, references, and evaluation cases. Use original
summaries and abstractions; do not copy therapeutic source material unless its license explicitly
permits this repository's use.

By contributing, you agree that your contribution is licensed under AGPL-3.0-or-later. Be
respectful, specific, and focused on the work in issues and reviews.
