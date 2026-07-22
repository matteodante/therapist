# Ricerca: memoria e framework per Therapist

Data: 22 luglio 2026.

## Conclusione

Per l'MVP conviene mantenere Flue e Hindsight, ma Hindsight deve essere un indice di richiamo secondario, non la fonte di verità clinica. I dati confermati dall'utente (profilo, obiettivi, preferenze, correzioni e consensi) dovrebbero vivere in uno storage applicativo strutturato, ispezionabile e modificabile. La trascrizione canonica resta in Flue.

## Cosa prescrive Flue

Flue usa il proprio database per il flusso conversazionale canonico, gli allegati, le submission e i workflow run. Dichiara esplicitamente che i dati applicativi devono essere conservati dall'applicazione o da sistemi esterni. Per Node raccomanda SQLite su singolo host e Postgres quando servono persistenza condivisa e più repliche. Non prescrive Hindsight né offre una memoria semantica di lungo periodo integrata.

Fonti:

- [Flue: Database](https://flueframework.com/docs/guide/database/)
- [Flue: Data Persistence API](https://flueframework.com/docs/api/data-persistence-api/)
- [Flue: Durable Agents](https://flueframework.com/docs/concepts/durable-execution/)
- [Flue: Tools](https://flueframework.com/docs/guide/tools/)

## Valutazione di Hindsight

Hindsight fornisce `retain`, `recall` e `reflect`, estrazione di fatti ed entità, ragionamento temporale e retrieval multi-strategia. È open source, self-hostable e dispone di client TypeScript. Pubblica risultati forti su benchmark generali di memoria a lungo termine.

Questi benchmark non dimostrano però adeguatezza clinica, sicurezza su dati sanitari, correttezza multilingue o assenza di distorsioni nell'estrazione. Per Therapist è prudente usare `retain` e `recall` con provenienza e correzioni esplicite, mantenendo disabilitati osservazioni e `reflect` finché non esistono valutazioni specifiche. Devono inoltre esistere cancellazione completa, retention, autenticazione, audit e isolamento per utente.

Fonti:

- [Hindsight: repository e documentazione ufficiale](https://github.com/vectorize-io/hindsight)
- [Hindsight Cloud: concetti Retain, Recall e Reflect](https://docs.hindsight.vectorize.io/)
- [Hindsight: limiti dichiarati dei benchmark](https://hindsight.vectorize.io/blog/2026/03/23/agent-memory-benchmark)

## Alternative a Flue

### Mastra

È l'alternativa TypeScript più coesa se si vuole ridurre il numero di servizi: integra agenti, workflow, memoria, storage, semantic recall, eval e osservabilità. Può sostituire sia parte dell'harness sia parte della memoria esterna. La migrazione avrebbe però un costo elevato e richiederebbe di ricostruire channel Telegram, sicurezza e persistenza già presenti.

- [Mastra](https://mastra.ai/)
- [Mastra: memoria degli agenti](https://mastra.ai/blog/agent-memory-guide)

### LangGraph.js

È preferibile quando il comportamento deve essere una macchina a stati esplicita, con checkpoint, pause, human-in-the-loop e percorsi controllabili. Distingue checkpointer di breve periodo e store di lungo periodo. Per un prodotto clinicamente sensibile offre maggiore controllo del flusso, al prezzo di più codice e orchestrazione.

- [LangGraph.js: persistence](https://langchain-ai.github.io/langgraphjs/how-tos/subgraph-persistence/)

### OpenAI Agents SDK

È una buona opzione se il prodotto sceglie OpenAI come piattaforma primaria. Offre sessioni persistenti, provider personalizzabili e tracing, ma rende meno naturale l'obiettivo local-first/Ollama e non risolve da solo la memoria clinica strutturata.

- [OpenAI Agents SDK: Sessions](https://openai.github.io/openai-agents-js/guides/sessions/)
- [OpenAI Agents SDK: Models](https://openai.github.io/openai-agents-js/guides/models/)

## Raccomandazione operativa

1. Conservare Flue come transcript canonico e runtime dell'MVP.
2. Conservare Hindsight come retrieval secondario, con `reflect` e osservazioni automatiche disabilitati.
3. Aggiungere una memoria strutturata applicativa per soli dati confermati dall'utente, con provenienza, timestamp, correzione e cancellazione.
4. Valutare Hindsight con scenari italiani specifici: contraddizioni, correzioni, eventi temporali, omonimie, falsi ricordi e rischio clinico.
5. Rivalutare Mastra se la priorità diventa semplificare lo stack; rivalutare LangGraph se la priorità diventa rendere esplicito e verificabile il protocollo clinico.
