# Security and privacy

## Threat model summary

Sensitive assets:

- conversation history;
- memories;
- working hypotheses;
- Telegram token;
- webhook secret;
- model and memory endpoints;
- future exports.

## Controls in the starter

- one numeric Telegram user allowlist;
- private chats only;
- verified Telegram webhook secret;
- durable update deduplication;
- no host shell or filesystem tools;
- no browser, MCP, generic HTTP, or code execution tools;
- trusted code selects Telegram destinations and memory banks;
- secrets in environment variables;
- content is not written to application logs;
- application-owned structured memory separated from the Hindsight derived index;
- local model, memory, and STT endpoints by default.

## Telegram limitation

Telegram bot chats are cloud chats, not Secret Chats. Even when inference and
memory are local, messages and voice files transit through Telegram.

## Voice

The application downloads a Telegram voice file into memory, sends it to the
configured local STT endpoint, and does not intentionally persist the audio.
The transcript is persisted as conversation content and memory input.

## Flue beta limitation

Flue's default agent sandbox includes file and command tools. Therapist replaces
the sandbox model tool factory with an empty list. Framework skill tools remain,
and `task` is not yet removable through the public profile API. No subagents are
declared, and task use is prohibited by instruction.

A production security review should verify the effective tool list on every
Flue upgrade.

## SaaS requirements

A hosted version must add:

- tenant authentication and authorization;
- per-tenant application records and Hindsight bank isolation;
- Postgres row/tenant isolation;
- encryption at rest and in transit;
- managed secrets;
- retention and deletion workflows;
- audit events without conversation content;
- abuse prevention;
- incident response;
- backups and disaster recovery;
- data processing and residency documentation.
