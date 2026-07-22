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
       ├── bounded Hindsight tools
       └── restricted sandbox
              ↓
         Ollama / Gemma 4
         oppure OpenAI Platform API

Canonical transcript → Flue SQLite
Long-term memory     → Hindsight
Voice transcription → Speaches
```

Flue orchestra l'agente e invoca Hindsight tramite tool applicativi. Hindsight
rimane un servizio distinto e usa direttamente il proprio provider LLM per
estrazione e retrieval; nel profilo locale quel provider è Ollama. Flue non è
un gateway obbligatorio per le chiamate interne dei servizi esterni.

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
- Hindsight bank IDs;
- tokens and endpoints.

The model controls only:

- memory query text;
- labeled process notes;
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

### Hindsight personal bank

Only user-originated messages and corrections. It answers: **what did the user
state or experience?**

### Hindsight process bank

Assistant replies and explicitly labeled working hypotheses, goals,
interventions, outcomes, preferences, and open questions. It answers:
**what has the process tentatively learned?**

This separation reduces the risk that the model's own interpretation becomes a
self-confirming personal fact.

## Telegram idempotency

`therapist-app.db` claims Telegram `update_id` values before dispatch. This
prevents webhook retries from creating duplicate turns.

## Local dependencies

- Ollama runs natively for hardware acceleration.
- Hindsight and Speaches can run through Docker Compose.
- The application can run on the host or under the optional Compose `app`
  profile.

## Future SaaS

For SaaS:

- Flue SQLite becomes Postgres;
- one routed owner handles each agent instance;
- Hindsight banks are tenant-isolated;
- Telegram or first-party clients authenticate at the application edge;
- secrets, encryption, retention, audit, and deletion become managed services.
