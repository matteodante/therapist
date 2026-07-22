import { registerProvider } from '@flue/runtime';
import { flue } from '@flue/runtime/routing';
import { Hono } from 'hono';
import { dependencyHealth } from './services/health.ts';
import { optionalEnv } from './shared/env.ts';

registerProvider('ollama', {
  api: 'openai-completions',
  baseUrl: optionalEnv('OLLAMA_BASE_URL', 'http://localhost:11434/v1'),
});

const app = new Hono();

app.get('/healthz', (c) =>
  c.json({
    ok: true,
    service: 'therapist',
    version: '0.1.0',
    timestamp: new Date().toISOString(),
  }),
);

app.get('/readyz', async (c) => {
  const health = await dependencyHealth();
  const ready = Object.values(health).every(
    (value) => typeof value === 'object' && value !== null && 'ok' in value && value.ok === true,
  );
  return c.json(health, ready ? 200 : 503);
});

app.route('/', flue());

export default app;
