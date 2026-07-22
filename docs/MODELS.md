# Modelli e provider

## Configurazione supportata

Therapist usa il model specifier configurato in `THERAPIST_MODEL`.

- `ollama/gemma4:12b` è il default locale. `src/app.ts` registra Ollama tramite
  il protocollo Flue `openai-completions` e `OLLAMA_BASE_URL`.
- `openai/<model-id>` usa il provider OpenAI integrato in Flue e richiede
  `OPENAI_API_KEY`. Non serve una seconda registrazione in `src/app.ts`.

Il model ID OpenAI va scelto dal catalogo supportato dalla versione Flue
installata e verificato con gli eval clinici del progetto prima dell'uso reale.

## Perché l'abbonamento Codex non è un backend di Therapist

OpenAI documenta il login ChatGPT come accesso in abbonamento per i client
Codex locali. Il Codex SDK controlla thread Codex orientati alla programmazione;
non espone un endpoint LLM generico equivalente alla Responses API da inserire
come provider Flue.

L'API OpenAI è inoltre fatturata e gestita separatamente da ChatGPT. Di
conseguenza il progetto non riutilizza token OAuth locali, endpoint privati di
ChatGPT o adapter non ufficiali. Per un bot sempre attivo le opzioni supportate
restano Ollama oppure OpenAI Platform API con API key.

Fonti ufficiali:

- [Flue: Models & Providers](https://flueframework.com/docs/guide/models/)
- [OpenAI: autenticazione Codex](https://learn.chatgpt.com/docs/auth)
- [OpenAI: Codex SDK](https://learn.chatgpt.com/docs/codex-sdk)
- [OpenAI: fatturazione ChatGPT e API separata](https://help.openai.com/en/articles/8156019-how-can-i-move-my-chatgpt-subscription-to-the-api)
