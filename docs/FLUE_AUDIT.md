# Flue compliance audit

Date: July 22, 2026. Verified versions: `@flue/runtime@1.0.0-beta.9` and
`@flue/telegram@1.0.0-beta.1`.

## Result

- `src/` is the canonical source directory.
- The agent is a `defineAgent(...)` default export directly under
  `src/agents/`.
- The channel exports the named `channel` binding directly under
  `src/channels/`.
- `src/app.ts` composes Hono, health checks, and `flue()`, and registers only
  the custom Ollama provider.
- Markdown instructions use `with { type: 'markdown' }`; Agent Skills use
  `with { type: 'skill' }`.
- Tools use `defineTool`, Valibot `input` and `output` schemas, and
  `run({ input, signal })`.
- Trusted code determines Telegram identity, destination, bank IDs, and
  credentials rather than the model.
- The application sandbox exposes no shell or filesystem access.
- Flue SQLite stores the canonical conversation; Hindsight is external
  application memory accessed through bounded tools.

## Applied corrections

- The channel now uses the Flue beta.9 form
  `dispatch(agent, { id, input })`.
- Message types derive from the `Update` exported by `@flue/telegram`, avoiding
  the version conflict between the `@grammyjs/types` packages used by Flue and
  grammY.
- Memory tools propagate the `AbortSignal` to the Hindsight client.
- Hindsight banks use the current `retainMission`, `reflectMission`, and
  explicit disposition properties.
- The lockfile and pnpm policy authorize only the required `esbuild` build
  script; optional build scripts remain denied.

## Verification

Completed successfully:

```text
pnpm validate:skills
pnpm typecheck
pnpm test
pnpm build
```

Reference guides:

- [Project Layout](https://flueframework.com/docs/guide/project-layout/)
- [Agents](https://flueframework.com/docs/guide/building-agents/)
- [Channels](https://flueframework.com/docs/guide/channels/)
- [Tools](https://flueframework.com/docs/guide/tools/)
- [Skills](https://flueframework.com/docs/guide/skills/)
- [Models & Providers](https://flueframework.com/docs/guide/models/)
- [Database](https://flueframework.com/docs/guide/database/)
- [Agent API](https://flueframework.com/docs/api/agent-api/)
