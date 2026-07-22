# Models and providers

## Supported configuration

Therapist uses the model specifier configured in `THERAPIST_MODEL`.

- `ollama/gemma4:12b` is the local default. `src/app.ts` registers Ollama with
  Flue's `openai-completions` protocol and `OLLAMA_BASE_URL`.
- `openai/<model-id>` uses Flue's built-in OpenAI provider and requires
  `OPENAI_API_KEY`. No additional registration is needed in `src/app.ts`.

Choose an OpenAI model ID from the catalog supported by the installed Flue
version and validate it against this project's clinical evaluations before
real-world use.

## Why a Codex subscription is not a Therapist backend

OpenAI documents ChatGPT sign-in as subscription access for local Codex
clients. The Codex SDK controls coding-focused Codex threads; it does not expose
a generic LLM endpoint equivalent to the Responses API that can be registered
as a Flue provider.

The OpenAI API is also billed and managed separately from ChatGPT. Therefore,
the project does not reuse local OAuth tokens, private ChatGPT endpoints, or
unofficial adapters. The supported options for an always-on bot remain Ollama
or the OpenAI Platform API with an API key.

Official sources:

- [Flue: Models & Providers](https://flueframework.com/docs/guide/models/)
- [OpenAI: Codex authentication](https://learn.chatgpt.com/docs/auth)
- [OpenAI: Codex SDK](https://learn.chatgpt.com/docs/codex-sdk)
- [OpenAI: separate ChatGPT and API billing](https://help.openai.com/en/articles/8156019-how-can-i-move-my-chatgpt-subscription-to-the-api)
