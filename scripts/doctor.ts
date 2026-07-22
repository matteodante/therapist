import { dependencyHealth } from '../src/services/health.ts';
import { optionalEnv } from '../src/shared/env.ts';

const required = [
  'TELEGRAM_BOT_TOKEN',
  'TELEGRAM_WEBHOOK_SECRET_TOKEN',
  'TELEGRAM_ALLOWED_USER_ID',
] as const;

let failed = false;

const [major, minor] = process.versions.node.split('.').map(Number);
if ((major ?? 0) < 22 || ((major ?? 0) === 22 && (minor ?? 0) < 19)) {
  console.error(`Node ${process.versions.node} is unsupported; use >=22.19.0.`);
  failed = true;
} else {
  console.log(`✓ Node ${process.versions.node}`);
}

for (const name of required) {
  if (!process.env[name]?.trim()) {
    console.error(`✗ ${name} is missing`);
    failed = true;
  } else {
    console.log(`✓ ${name}`);
  }
}

console.log(`Model: ${optionalEnv('THERAPIST_MODEL', 'ollama/gemma4:12b')}`);

try {
  const health = await dependencyHealth();
  console.log(JSON.stringify(health, null, 2));
  const unhealthy = Object.entries(health).filter(
    ([, value]) => typeof value !== 'object' || value === null || !('ok' in value) || value.ok !== true,
  );
  if (unhealthy.length > 0) failed = true;
} catch (error) {
  console.error(error);
  failed = true;
}

process.exitCode = failed ? 1 : 0;
