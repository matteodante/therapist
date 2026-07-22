# Research: Vercel Eve as an alternative to Flue

Date: July 22, 2026. Sources reviewed: Vercel/Eve documentation and the
official `vercel/eve` repository.

## Conclusion

Eve is currently the Flue alternative closest to Therapist's architecture. It
is TypeScript and filesystem-first, and includes persistent agents, Markdown
skills, typed tools, evaluations, approvals, sandboxes, and an official
Telegram channel. It can use Ollama and can be fully self-hosted.

It does not solve the main clinical-memory problem. Eve persists transcripts,
workflows, and individual session state, but explicitly does not provide
tenant-aware long-term memory. Hindsight or, preferably, structured application
storage would remain separate.

The MVP should not migrate immediately. The Flue project already exists, and a
migration would not reduce the number of memory components. A small isolated
Eve spike would be more useful. If Telegram, restart recovery, local tool
calling, and data deletion pass testing, Eve could become a stronger future
migration candidate than Mastra.

## Comparison with the current architecture

| Therapist requirement | Eve | Assessment |
| --- | --- | --- |
| Agent and instructions | `agent/instructions.md` and `agent/agent.ts` | Conceptually equivalent to Flue |
| Reusable protocols | `agent/skills/*.md`, loaded on demand | Good fit for the current clinical skills |
| Bounded tools | `agent/tools/*.ts`, Zod, optional approval | Suitable; derive tenant and user from verified context |
| Persistent conversations | Durable, checkpointed workflow sessions | Yes; transcript and run state belong to the workflow |
| Short-term memory | `defineState`, durable within one session | Does not replace Hindsight |
| Long-term memory | External database, KV, or vector store through tools and dynamic instructions | Must be built; no native Eve subsystem |
| Telegram | Official channel with webhooks, attachments, and HITL | Better coverage than a custom adapter |
| Cloud and local models | AI Gateway or any AI SDK `LanguageModel` | OpenAI, other providers, and Ollama are possible |
| Self-hosting | Replaceable Node/Nitro workflow storage and sandboxes | Supported, but production configuration remains involved |

## Architecture and persistence

Eve compiles an `agent/` directory and mounts a durable HTTP runtime. Each
conversation is a workflow session: steps are checkpointed, can wait for a
message or approval, and resume after a crash or deployment.

In local and self-hosted environments, the default workflow state lives in
`.eve/.workflow-data`, which must be mounted on persistent storage. For multiple
replicas, Eve supports an external Workflow "world," such as PostgreSQL, but
this configuration is experimental and must use the matching Workflow SDK beta
line.

`defineState` preserves typed state for the lifetime of one session, not across
sessions. The official multi-tenant-memory guide instead prescribes an external
application store, always scoped by verified identity, with tools for writes
and deletion and dynamic instructions for retrieval. The recommended Therapist
separation therefore remains:

```text
Eve workflow store      -> canonical session transcript and state
Application database    -> confirmed facts, consent, corrections, retention
Hindsight (optional)    -> secondary, fallible semantic retrieval
```

## Providers, Ollama, and ChatGPT subscriptions

A string such as `openai/...` normally routes through Vercel AI Gateway. Eve
also accepts an AI SDK `LanguageModel` object, allowing direct calls to cloud
or local providers without the Gateway.

Ollama can be used through a compatible AI SDK provider or through
`@ai-sdk/openai-compatible` pointed at the local endpoint. The Ollama
integration documented by the AI SDK is community-maintained, so replacing
Flue would require model-specific tests for tool calling, streaming, images,
context handling, and errors.

Eve 0.27 also exposes `experimental_chatgpt()` from `eve/models/openai`. It uses
the local Codex login (`codex login`) and charges usage to the ChatGPT
subscription. However, it is documented for local execution only, fails in
deployment, uses a non-public backend, and may break without notice. It is not
a reliable foundation for an always-on Telegram bot. API keys, the Gateway, or
Ollama remain preferable in production.

## Telegram and webhooks

The official `eve/channels/telegram` channel mounts `POST /eve/v1/telegram`,
verifies `X-Telegram-Bot-Api-Secret-Token`, and handles private and group chats,
HITL callbacks, proactive messages, photos, and documents. The application is
still responsible for `setWebhook` registration.

Verifying the Telegram secret alone is insufficient for Therapist's
single-user constraint. `onMessage` must compare verified identity with the
authorized user and return `null` for every other sender. The session or
continuation key must also avoid collisions across chats, threads, and users.

## Security

Eve separates the trusted application runtime from the sandbox. Secrets and
application tools remain in the runtime, while shell and filesystem access are
confined to `/workspace`. Authenticated ingress fails closed by default, and
official channels verify signatures or tokens.

The default is not suitable for Therapist without hardening. The model receives
`bash`, file read and write, glob, and grep; sandbox egress defaults to
`allow-all`; and custom tools without a policy require no approval. Eve allows
removing built-ins with `disableTool()` and setting egress to `deny-all`. A
migration must preserve the current boundary: no shell, files, web access, or
subagents; narrowly bounded memory tools; and trusted-code control of identity
and destination.

For psychological data, encryption, retention, export and deletion, auditing,
data residency, provider and telemetry selection, consent, and clinical
governance remain product responsibilities. Eve does not claim healthcare
validation, and its Responsible Use guide assigns these choices to the
deployer.

## Hosting and maturity

The framework is open source under Apache-2.0. On July 22, 2026, the official
repository publishes `eve@0.27.0` and still labels it beta. APIs,
documentation, and behavior may change. Eve was announced publicly on June 17,
2026, so it has less public operational history than its feature set might
suggest.

Self-hosting is real: `eve build` and `eve start`, local storage or a PostgreSQL
Workflow world, Docker, microsandbox, or custom sandboxes, and reverse proxies
for `/eve/` and `/.well-known/workflow/`. It is not zero-operations: TLS,
storage, backups, workflow callbacks, the schedule runner, sandboxes,
authentication, and observability still require management. Vercel's path is
more integrated and mature, but increases platform dependence and requires
particular care for sensitive data.

## Recommendation

1. Do not migrate the main product now.
2. Build an Eve spike with one protocol, single-user Telegram, and unchanged
   Hindsight integration.
3. Disable every unnecessary built-in tool and deny sandbox egress.
4. Test both Ollama and the OpenAI API; consider `experimental_chatgpt()` only
   as a local development convenience.
5. Test restart recovery, duplicate webhooks, memory correction and deletion,
   user isolation, voice attachments, and clinical-risk scenarios.
6. Migrate only if Eve measurably reduces operational code or improves
   durability and approvals without weakening privacy or control.

## Official sources

- [Eve overview](https://vercel.com/eve)
- [Introducing Eve](https://vercel.com/blog/introducing-eve)
- [Official `vercel/eve` repository](https://github.com/vercel/eve)
- [Agent and model configuration](https://eve.dev/docs/agent-config)
- [TypeScript API, including `experimental_chatgpt()`](https://eve.dev/docs/reference/typescript-api)
- [Telegram channel](https://eve.dev/docs/channels/telegram)
- [Self-hosting](https://eve.dev/docs/guides/deployment/self-hosting)
- [Durable per-session state](https://eve.dev/docs/guides/state)
- [Official multi-tenant-memory pattern](https://eve.dev/docs/patterns/multi-tenant-memory)
- [Security model](https://eve.dev/docs/concepts/security-model)
- [Responsible Use](https://eve.dev/docs/responsible-use)
- [AI SDK: providers and self-hosted models](https://ai-sdk.dev/docs/foundations/providers-and-models)
- [AI SDK: Ollama provider](https://ai-sdk.dev/providers/community-providers/ollama)
