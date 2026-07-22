import { optionalEnv } from '../shared/env.ts';

async function fetchStatus(url: string, timeout = 5000): Promise<Record<string, unknown>> {
  const response = await fetch(url, { signal: AbortSignal.timeout(timeout) });
  return {
    ok: response.ok,
    status: response.status,
  };
}

export async function dependencyHealth(): Promise<Record<string, unknown>> {
  const ollamaBase = optionalEnv('OLLAMA_BASE_URL', 'http://localhost:11434/v1');
  const ollamaRoot = ollamaBase.replace(/\/v1\/?$/, '').replace(/\/+$/, '');
  const sttBase = optionalEnv('STT_BASE_URL', 'http://localhost:8000').replace(/\/+$/, '');

  const [ollama, stt] = await Promise.allSettled([
    fetchStatus(`${ollamaRoot}/api/tags`),
    fetchStatus(`${sttBase}/health`),
  ]);

  const summarize = (result: PromiseSettledResult<Record<string, unknown>>) =>
    result.status === 'fulfilled'
      ? result.value
      : { ok: false, error: result.reason instanceof Error ? result.reason.message : String(result.reason) };

  return {
    app: { ok: true },
    ollama: summarize(ollama),
    stt: summarize(stt),
  };
}
