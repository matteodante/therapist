# Implementation guide

## Agent initialization

`src/agents/therapist.ts` imports permanent instructions and ten packaged Agent
Skills, creates bounded memory tools, binds the Telegram destination, and uses a
restricted sandbox.

## Telegram ingress

`src/channels/telegram.ts`:

1. verifies the webhook through `@flue/telegram`;
2. accepts only the configured private user;
3. claims `update_id`;
4. transcribes voice when necessary;
5. retains the user message;
6. dispatches to the persistent Flue agent.

The model posts the final reply through a destination-bound tool.

## Memory

`src/services/hindsight.ts` owns bank naming and never exposes bank IDs to the
model. Personal and process memory are separate.

## Persistence

- `src/db.ts` configures file-backed Flue SQLite.
- `src/storage/app-db.ts` stores Telegram update IDs.

## Provider

`src/app.ts` registers Ollama as an OpenAI-compatible Flue provider.
I provider inclusi in Flue, come `openai`, non richiedono registrazione:
selezionare `openai/<model-id>` e fornire `OPENAI_API_KEY`. Vedi
`docs/MODELS.md` per il confine tra API OpenAI e abbonamento ChatGPT/Codex.

## Adding a skill

1. create `src/skills/<name>/SKILL.md`;
2. use Agent Skills-compatible frontmatter;
3. add references and eval scenarios;
4. import it in `src/agents/therapist.ts`;
5. run `pnpm validate:skills`;
6. obtain required review.

## Adding a tool

A tool must be:

- narrow;
- bound to trusted user/destination context;
- schema-validated;
- free of model-selected credentials or tenant IDs;
- documented in the threat model.

Do not expose arbitrary file, shell, URL, database, or provider operations.
