import { optionalEnv, requiredEnv } from '../src/shared/env.ts';

const token = requiredEnv('TELEGRAM_BOT_TOKEN');
const secret = requiredEnv('TELEGRAM_WEBHOOK_SECRET_TOKEN');
const publicBaseUrl = requiredEnv('PUBLIC_BASE_URL').replace(/\/+$/, '');
const webhookUrl = `${publicBaseUrl}/channels/telegram/webhook`;

const response = await fetch(`https://api.telegram.org/bot${token}/setWebhook`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: webhookUrl,
    secret_token: secret,
    allowed_updates: ['message'],
    drop_pending_updates: optionalEnv('TELEGRAM_DROP_PENDING_UPDATES', 'false') === 'true',
  }),
});

const payload = await response.json();
if (!response.ok || !(payload as { ok?: boolean }).ok) {
  console.error(payload);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ webhookUrl, result: payload }, null, 2));
}
