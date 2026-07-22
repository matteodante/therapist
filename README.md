# Therapist

**Therapist** is an open-source, self-hosted therapy agent: a persistent AI
companion designed to follow evidence-informed psychological processes,
remember a person's history, formulate hypotheses collaboratively, and help
evaluate concrete change over time.

> **Project status: research-grade starter, not a clinically validated
> treatment and not a substitute for a licensed mental-health professional or
> emergency service.**

## What makes it different

Therapist is not intended to be a generic empathetic chatbot. Its desired loop is:

```text
listen
→ recall relevant history
→ understand content, meaning, and process
→ consider alternative hypotheses
→ ask one useful question
→ formulate collaboratively
→ choose an appropriate intervention
→ check the outcome
→ update memory
```

## Stack

- **Flue 1.0 beta** — persistent agent harness and Agent Skills
- **TypeScript** — application code and bounded tools
- **Ollama + Gemma 4 12B** — default local model
- **OpenAI Platform API** — optional Flue built-in provider
- **Hindsight** — derived semantic recall index
- **Node SQLite** — structured, user-confirmed memory
- **Flue SQLite** — canonical conversation stream
- **Telegram** — text and voice interface
- **Speaches** — local OpenAI-compatible speech-to-text

The model does **not** receive host shell or filesystem tools. Therapist uses a
restricted Flue sandbox whose model-facing sandbox tool list is empty. The only
application tools are memory operations and posting to the bound Telegram chat.
Flue's framework-owned skill activation remains available. Flue beta currently
also exposes its framework `task` capability; the agent instructions prohibit
its use and no subagents are configured.

## Product scope

The initial product focuses on adults and low-to-moderate, non-complex concerns:

- stress and anxiety;
- worry and rumination;
- avoidance and procrastination;
- self-criticism and perfectionism;
- low mood and reduced activity;
- non-acute relationship difficulties;
- values, goals, and problem solving.

Read [`docs/PRODUCT.md`](docs/PRODUCT.md) and
[`docs/SCOPE.md`](docs/SCOPE.md) before contributing.

## Quick start

### Requirements

- Node.js `>=22.19.0`
- pnpm `>=11`
- Ollama
- Docker Desktop or Docker Engine for Hindsight and Speaches
- a Telegram bot token
- a public HTTPS URL for Telegram webhook delivery during local development
  (for example a tunnel)

### 1. Install and pull the model

```bash
ollama pull gemma4:12b
corepack enable
corepack prepare pnpm@11.1.1 --activate
pnpm install
```

### 2. Configure

```bash
cp .env.example .env
```

Set at least:

```dotenv
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBHOOK_SECRET_TOKEN=...
TELEGRAM_ALLOWED_USER_ID=...
PUBLIC_BASE_URL=https://your-public-host.example
```

Generate a webhook secret with letters, numbers, `_`, or `-`.

Ollama remains the default provider. To use the OpenAI API instead, set a Flue
`openai/...` model specifier in `THERAPIST_MODEL` and configure
`OPENAI_API_KEY`. API billing is separate from a ChatGPT/Codex subscription;
see [`docs/MODELS.md`](docs/MODELS.md).

### 3. Start local dependencies

```bash
docker compose up -d hindsight speaches
```

Download the configured STT model using the Speaches CLI:

```bash
SPEACHES_BASE_URL=http://localhost:8000 \
  uvx speaches-cli model download Systran/faster-whisper-small
```

### 4. Start Therapist

```bash
pnpm dev
```

Flue development mode listens on port `3583`.

### 5. Configure the Telegram webhook

```bash
pnpm telegram:set-webhook
```

Telegram sends updates to:

```text
POST /channels/telegram/webhook
```

### 6. Validate the installation

```bash
pnpm doctor
pnpm check
```

## Run the application in Docker

Ollama is intentionally expected on the host so Apple Silicon and Windows can
use their native acceleration.

```bash
docker compose --profile app up -d
```

Set `OLLAMA_DOCKER_BASE_URL` when Ollama is on another machine.

## Repository map

```text
src/
  agents/         Therapist agent definition
  channels/       Telegram webhook and outbound tool
  instructions/   Permanent agent operating instructions
  sandboxes/      Restricted no-shell/no-file sandbox policy
  services/       Hindsight, STT, health checks
  skills/         Evidence-informed Agent Skills
  storage/        Telegram idempotency and structured memory
  tools/          Bounded structured and semantic memory tools
docs/             Product, scope, clinical method, security, SaaS plan
scripts/          Doctor and webhook setup
```

## Important limitations

- The bundled protocols are **drafts requiring professional clinical review**.
- Memory extraction by local models can miss or distort facts.
- A convincing formulation is not necessarily a correct formulation.
- Telegram bot chats are not end-to-end encrypted.
- Hindsight and Flue are both pinned because their APIs are evolving.
- `gemma4:12b` is a default, not a guarantee of adequate clinical quality.

## Repository GitHub

The repository is private and available at
[`matteodante/therapist`](https://github.com/matteodante/therapist).

## License

Application code and original project documentation are Apache-2.0. Clinical
sources and adapted materials keep their own licenses. See
[`docs/SOURCES.md`](docs/SOURCES.md) and [`NOTICE`](NOTICE).
