# Architecture

```text
Telegram webhook
       ↓
verified, single-user channel
       ↓
Flue persistent agent instance
       ├── permanent instructions
       ├── Agent Skills
       ├── bounded Telegram post tool
       ├── bounded memory tools
       └── restricted sandbox
              ↓
         Ollama / Gemma 4
         or OpenAI Platform API

Canonical transcript → Flue SQLite
Curated memory       → Markdown vault
Voice transcription → Speaches
```

Flue orchestrates the agent and exposes bounded application tools for the
Markdown vault. The model has no generic filesystem access.

## Why Flue

Flue provides:

- persistent addressable agents;
- canonical append-only conversations;
- SQLite on Node;
- durable dispatch;
- Agent Skills;
- bounded typed tools;
- Telegram channel package;
- local and hosted deployment targets.

The project pins Flue beta versions and isolates integration code because the
framework is evolving.

## One agent

Therapist uses one primary agent. Psychological judgment remains in the model,
guided by permanent instructions and on-demand skills.

There is no separate planner, supervisor agent, or multi-agent clinical
hierarchy in the MVP.

## Tool boundary

Trusted code binds:

- Telegram destination;
- authorized user;
- memory vault path and filenames;
- tokens and endpoints.

The model controls only:

- curated memory content;
- final reply text.

A custom Flue sandbox replaces default bash, read, write, edit, grep, and glob
tools with an empty sandbox tool list. No local host sandbox is used.

Flue beta still appends framework-owned `activate_skill`, skill-resource access,
and `task`. No subagents are declared, the instructions prohibit `task`, and
any child session inherits the same restricted boundary. This should be
revisited when Flue exposes a first-class single-agent mode.

## Data separation

### Flue SQLite

Canonical conversation and tool history. It answers: **what happened?**

### Application SQLite

Telegram update IDs only. It prevents webhook retries from creating duplicate
turns.

### Markdown vault

`SELF.md` contains user-stated context. `JOURNEY.md` contains separate
assistant-authored therapy-process notes with supporting evidence. It answers:
**what concise context should affect future conversations?**

Assistant replies and full session history remain only in Flue's canonical
conversation stream.

## Telegram idempotency

`therapist-app.db` claims Telegram `update_id` values before dispatch. This
prevents webhook retries from creating duplicate turns.

## Local dependencies

- Ollama runs natively for hardware acceleration.
- Speaches can run through Docker Compose.
- The application can run on the host or under the optional Compose `app`
  profile.

## Future SaaS

For SaaS:

- Flue SQLite becomes Postgres;
- one routed owner handles each agent instance;
- memory vaults are tenant-isolated;
- Telegram or first-party clients authenticate at the application edge;
- secrets, encryption, retention, audit, and deletion become managed services.

The hosted edition must preserve portable exports of the canonical transcript,
Markdown memory, and protocol versions so a user can move between hosted and
self-hosted deployments without data lock-in.
