# Self-hosting

## Recommended topology

```text
Host:
  Ollama
  Therapist Node server

Docker:
  Hindsight
  Speaches
```

This allows native Ollama acceleration on Apple Silicon and Windows while
keeping supporting services easy to start.

## Setup

1. Install Node 22.19+, pnpm 11, Ollama, Docker, and `uvx`.
2. Pull `gemma4:12b`.
3. Copy `.env.example` to `.env`.
4. Start Hindsight and Speaches.
5. Download the STT model.
6. Run `pnpm dev`.
7. expose port 3583 through HTTPS;
8. run `pnpm telegram:set-webhook`.

## Network exposure

Only the public Telegram webhook needs Internet ingress. Ollama, Hindsight,
Speaches, health routes, and databases should not be exposed publicly.

## Backups

Back up:

- `data/flue.db`;
- `data/therapist-app.db`;
- Hindsight's `hindsight_pg` volume;
- `.env` separately and securely;
- protocol and configuration versions.

Do not copy live SQLite files without a consistent backup method.

## Upgrades

- pin dependency versions;
- back up before upgrading;
- run `pnpm check`;
- inspect the effective Flue tool boundary;
- test memory recall and Telegram delivery;
- review protocol changes separately from code changes.
