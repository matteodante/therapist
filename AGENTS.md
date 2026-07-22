# Istruzioni per gli agenti di sviluppo

## Lingua e stile

- Rispondi sempre in italiano, in modo conciso ma completo.
- Mantieni nomi, API e termini tecnici di Flue nella forma usata dalla documentazione ufficiale.

## Documentazione Flue obbligatoria

Prima di creare o modificare codice che coinvolge Flue, recupera e consulta sempre le guide ufficiali correnti su <https://flueframework.com/docs/>. Non affidarti soltanto alla memoria, a esempi locali o a API presunte.

Consulta almeno la guida pertinente alla modifica:

- struttura del progetto: <https://flueframework.com/docs/guide/project-layout/>
- agenti: <https://flueframework.com/docs/guide/building-agents/>
- skill: <https://flueframework.com/docs/guide/skills/>
- tool: <https://flueframework.com/docs/guide/tools/>
- sandbox: <https://flueframework.com/docs/guide/sandboxes/>
- routing e `app.ts`: <https://flueframework.com/docs/guide/routing/>
- API degli agenti: <https://flueframework.com/docs/api/agent-api/>

Se la documentazione corrente e la versione di Flue fissata in `package.json` non coincidono, verifica anche i tipi e le API effettivamente installati. Non aggiornare Flue o altre dipendenze senza una richiesta esplicita.

## Struttura Flue da rispettare

- Usa `src/` come source directory canonica.
- Mantieni gli agenti direttamente in `src/agents/`, senza agenti annidati. Usa file `lower-kebab-case.ts` e un `default export` creato con `defineAgent(...)`.
- Mantieni `src/app.ts` come composizione Hono per middleware, health check e mount di `flue()`.
- Mantieni i channel direttamente in `src/channels/`; ogni channel scoperto da Flue deve esportare il binding nominato `channel`.
- Usa `src/workflows/` soltanto per operazioni finite con input e risultato, non per conversazioni persistenti.
- Conserva istruzioni lunghe in file Markdown dedicati e importale con l'attributo previsto dalla versione Flue in uso.
- Conserva le Agent Skills applicative in `src/skills/<nome-skill>/SKILL.md`. Il nome della directory deve coincidere con il campo `name` del frontmatter. Importa le skill con `with { type: 'skill' }` e registrale nella configurazione dell'agente.
- Usa un tool per capacità eseguibili e limitate; usa una skill per istruzioni e procedure riutilizzabili; usa un workflow per lavoro finito controllato dall'applicazione.

## Sicurezza e confini

- Definisci i tool con `defineTool`, nomi chiari, input e output Valibot e `run({ input, signal })` secondo le API correnti.
- Considera ogni input scelto dal modello non attendibile. Credenziali, identità utente, tenant, destinazioni e limiti di autorizzazione devono essere determinati dal codice fidato.
- Mantieni il principio del minimo privilegio. Non ampliare sandbox, accesso a shell, filesystem, rete o credenziali senza una necessità esplicita e documentata.
- Per questo progetto preserva il sandbox ristretto e il vincolo single-user di Telegram, salvo richiesta esplicita accompagnata da una revisione di sicurezza.
- Mantieni separate la memoria personale dichiarata dall'utente e le note di processo generate dall'assistente.

## Verifica delle modifiche

Dopo ogni modifica rilevante esegui i controlli proporzionati al cambiamento. Come minimo usa:

```bash
pnpm typecheck
pnpm test
```

Per modifiche ad agenti, skill, routing o packaging esegui anche:

```bash
pnpm validate:skills
pnpm build
```

Non dichiarare completata una modifica se i controlli necessari non sono stati eseguiti; indica chiaramente eventuali verifiche non disponibili e il motivo.
