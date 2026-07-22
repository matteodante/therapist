# Ricerca: Vercel Eve come alternativa a Flue

Data: 22 luglio 2026. Fonti consultate: documentazione Vercel/Eve e repository ufficiale `vercel/eve`.

## Conclusione

Eve è oggi l'alternativa a Flue più vicina all'architettura di Therapist: è TypeScript, filesystem-first, include agenti persistenti, skill Markdown, tool tipizzati, eval, approvazioni, sandbox e un canale Telegram ufficiale. Può usare Ollama e può essere interamente self-hosted.

Non risolve però il problema principale della memoria clinica: Eve persiste transcript, workflow e stato della singola sessione, ma dichiara esplicitamente di non avere una memoria long-term tenant-aware. Hindsight o, preferibilmente, uno storage applicativo strutturato restano separati.

Per l'MVP non migrerei subito: il progetto Flue esiste già e una migrazione non ridurrebbe il numero di componenti della memoria. Preparerei invece un piccolo spike Eve isolato; se Telegram, restart, tool calling locale e cancellazione dei dati superano i test, Eve diventa una candidata più forte di Mastra per una futura migrazione.

## Confronto con l'architettura attuale

| Esigenza di Therapist | Eve | Valutazione |
| --- | --- | --- |
| Agente e istruzioni | `agent/instructions.md` e `agent/agent.ts` | Equivalente concettuale a Flue |
| Protocolli riutilizzabili | `agent/skills/*.md`, caricati on demand | Buon adattamento delle skill cliniche correnti |
| Tool limitati | `agent/tools/*.ts`, Zod, approval opzionale | Adeguato; tenant e utente vanno derivati dal contesto verificato |
| Conversazioni persistenti | Sessioni come workflow durevoli e checkpointed | Sì; transcript e run state sono parte del workflow |
| Memoria breve | `defineState`, durevole ma solo per sessione | Non sostituisce Hindsight |
| Memoria lunga | Database/KV/vector store esterno tramite tool e dynamic instructions | Da costruire; nessun sottosistema Eve nativo |
| Telegram | Canale ufficiale con webhook, allegati e HITL | Migliore copertura rispetto a un adapter custom |
| Modelli cloud/locali | AI Gateway o qualunque `LanguageModel` AI SDK | OpenAI, altri provider e Ollama sono possibili |
| Self-hosting | Node/Nitro, workflow storage e sandbox sostituibili | Sì, ma la configurazione production è ancora articolata |

## Architettura e persistenza

Eve compila una directory `agent/` e monta un runtime HTTP durevole. Ogni conversazione è una sessione workflow: i passaggi sono checkpointed, possono attendere un messaggio o un'approvazione e riprendono dopo crash o deploy.

In locale/self-hosted lo stato workflow predefinito vive in `.eve/.workflow-data`; la directory deve essere montata su storage persistente. Per più repliche Eve consente un Workflow “world” esterno, per esempio PostgreSQL, ma questa configurazione è sotto `experimental` e deve usare la stessa linea beta del Workflow SDK.

`defineState` conserva stato tipizzato per tutta la vita della sessione, non tra sessioni. La guida ufficiale sulla memoria multi-tenant prescrive invece un archivio applicativo esterno, sempre scoped da identità verificata, esposto tramite tool per scrivere/cancellare e dynamic instructions per recuperare. Per Therapist la separazione raccomandata rimane quindi:

```text
Eve workflow store      -> transcript e stato canonico della sessione
DB applicativo          -> fatti confermati, consensi, correzioni, retention
Hindsight (opzionale)   -> retrieval semantico secondario e fallibile
```

## Provider, Ollama e abbonamento ChatGPT

Una stringa come `openai/...` passa normalmente da Vercel AI Gateway. Eve accetta anche un oggetto `LanguageModel` dell'AI SDK, quindi può chiamare direttamente provider cloud o locali senza Gateway.

Ollama è utilizzabile tramite un provider AI SDK compatibile o tramite `@ai-sdk/openai-compatible` verso l'endpoint locale. L'integrazione Ollama documentata dall'AI SDK è community-maintained, quindi prima di sostituire Flue servono test specifici su tool calling, streaming, immagini, contesto e gestione degli errori del modello scelto.

Eve 0.27 espone inoltre `experimental_chatgpt()` da `eve/models/openai`: usa il login locale di Codex (`codex login`) e addebita l'uso all'abbonamento ChatGPT. È però dichiarato solo per esecuzione locale, fallisce in deployment, usa un backend non pubblico e può rompersi senza preavviso. Non è quindi una base affidabile per un bot Telegram sempre attivo; in produzione restano preferibili API key/Gateway o Ollama.

## Telegram e webhook

Il canale ufficiale `eve/channels/telegram` monta `POST /eve/v1/telegram`, verifica `X-Telegram-Bot-Api-Secret-Token`, gestisce chat private e gruppi, callback HITL, invii proattivi, foto e documenti. La registrazione `setWebhook` resta a carico dell'applicazione.

Per il vincolo single-user di Therapist non basta la verifica del secret Telegram: occorre personalizzare `onMessage`, confrontare l'identità verificata con l'utente autorizzato e restituire `null` per ogni altro mittente. La chiave di sessione/continuation deve inoltre evitare collisioni fra chat, thread e utenti.

## Sicurezza

Eve separa app runtime fidato e sandbox. Segreti e tool applicativi restano nel runtime; shell e filesystem sono confinati in `/workspace`. Gli ingressi autenticati falliscono chiusi per default e i channel ufficiali verificano le firme/token.

Il default non è adatto a Therapist senza hardening: il modello riceve `bash`, lettura/scrittura file, glob e grep; l'egress sandbox è `allow-all`; i tool custom senza policy non richiedono approvazione. Eve consente di rimuovere i built-in con `disableTool()` e impostare `deny-all`. Una migrazione deve replicare il confine attuale: niente shell/file/web, niente subagent, tool memoria strettamente limitati e identità/destinazioni decise solo dal codice fidato.

Per dati psicologici restano responsabilità del prodotto: cifratura, retention, export/delete, audit, data residency, selezione di provider e telemetry, consenso e governance clinica. Eve non dichiara una validazione sanitaria e la propria guida Responsible Use attribuisce queste scelte al deployer.

## Hosting e maturità

Il framework è open source con licenza Apache-2.0. Al 22 luglio 2026 il repository ufficiale pubblica `eve@0.27.0`, ma lo dichiara ancora beta: API, documentazione e comportamento possono cambiare. Eve è stato annunciato pubblicamente il 17 giugno 2026, quindi ha meno storico operativo pubblico di quanto suggerisca la ricchezza delle feature.

Il self-hosting è reale: `eve build`/`eve start`, storage locale o Workflow world PostgreSQL, sandbox Docker/microsandbox/custom e reverse proxy per `/eve/` e `/.well-known/workflow/`. Non è però “zero ops”: bisogna gestire TLS, storage, backup, callback workflow, schedule runner, sandbox, autenticazione e osservabilità. La strada Vercel è più pronta e integrata, ma aumenta la dipendenza dalla piattaforma e va valutata con particolare cautela per dati sensibili.

## Raccomandazione

1. Non migrare ora il prodotto principale.
2. Creare uno spike Eve con un solo protocollo, Telegram single-user e Hindsight invariato.
3. Disabilitare tutti i tool built-in non necessari e negare l'egress sandbox.
4. Provare sia Ollama sia OpenAI API; considerare `experimental_chatgpt()` solo come comodità di sviluppo locale.
5. Testare restart, duplicati webhook, correzione/cancellazione memoria, isolamento utente, allegati vocali e scenari di rischio clinico.
6. Migrare soltanto se Eve riduce davvero il codice operativo o offre durabilità/approvazioni misurabilmente migliori senza indebolire privacy e controllo.

## Fonti ufficiali

- [Eve: panoramica](https://vercel.com/eve)
- [Introduzione di Vercel a Eve](https://vercel.com/blog/introducing-eve)
- [Repository ufficiale `vercel/eve`](https://github.com/vercel/eve)
- [Configurazione agente e modelli](https://eve.dev/docs/agent-config)
- [API TypeScript, incluso `experimental_chatgpt()`](https://eve.dev/docs/reference/typescript-api)
- [Canale Telegram](https://eve.dev/docs/channels/telegram)
- [Self-hosting](https://eve.dev/docs/guides/deployment/self-hosting)
- [Stato durevole per sessione](https://eve.dev/docs/guides/state)
- [Pattern ufficiale per memoria multi-tenant](https://eve.dev/docs/patterns/multi-tenant-memory)
- [Modello di sicurezza](https://eve.dev/docs/concepts/security-model)
- [Responsible Use](https://eve.dev/docs/responsible-use)
- [AI SDK: provider e modelli self-hosted](https://ai-sdk.dev/docs/foundations/providers-and-models)
- [AI SDK: provider Ollama](https://ai-sdk.dev/providers/community-providers/ollama)
