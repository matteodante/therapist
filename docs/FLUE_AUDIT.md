# Audit di conformità Flue

Data: 22 luglio 2026. Versione verificata: `@flue/runtime@1.0.0-beta.9` e
`@flue/telegram@1.0.0-beta.1`.

## Esito

- `src/` è la source directory canonica.
- L'agente è un default export `defineAgent(...)` direttamente in
  `src/agents/`.
- Il channel espone il binding nominato `channel` direttamente in
  `src/channels/`.
- `src/app.ts` compone Hono, health check e `flue()` e registra il solo provider
  custom Ollama.
- Le istruzioni Markdown usano `with { type: 'markdown' }`; le Agent Skills
  usano `with { type: 'skill' }`.
- I tool usano `defineTool`, schemi Valibot `input`/`output` e
  `run({ input, signal })`.
- Identità Telegram, destinazione, bank ID e credenziali sono determinate dal
  codice fidato, non dal modello.
- Il sandbox applicativo non espone shell o filesystem.
- Flue SQLite conserva la conversazione canonica; Hindsight è memoria
  applicativa esterna richiamata con tool limitati.

## Correzioni applicate

- Il channel ora usa la forma Flue beta.9 `dispatch(agent, { id, input })`.
- I tipi dei messaggi derivano dall'`Update` esportato da `@flue/telegram`,
  evitando il conflitto tra le versioni `@grammyjs/types` di Flue e grammY.
- I tool memoria propagano l'`AbortSignal` al client Hindsight.
- Le bank Hindsight usano le proprietà correnti `retainMission`,
  `reflectMission` e i campi di disposition espliciti.
- Il lockfile e la policy pnpm autorizzano soltanto il build script necessario
  di `esbuild`; i build script opzionali restano negati.

## Verifiche

Eseguite con esito positivo:

```text
pnpm validate:skills
pnpm typecheck
pnpm test
pnpm build
```

Guide di riferimento:

- [Project Layout](https://flueframework.com/docs/guide/project-layout/)
- [Agents](https://flueframework.com/docs/guide/building-agents/)
- [Channels](https://flueframework.com/docs/guide/channels/)
- [Tools](https://flueframework.com/docs/guide/tools/)
- [Skills](https://flueframework.com/docs/guide/skills/)
- [Models & Providers](https://flueframework.com/docs/guide/models/)
- [Database](https://flueframework.com/docs/guide/database/)
- [Agent API](https://flueframework.com/docs/api/agent-api/)
