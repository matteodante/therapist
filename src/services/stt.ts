import type { Api } from 'grammy';
import { optionalEnv, optionalNumber } from '../shared/env.ts';

const MAX_AUDIO_BYTES = 20 * 1024 * 1024;

export async function transcribeTelegramVoice(
  client: Api,
  botToken: string,
  fileId: string,
  reportedSize?: number,
): Promise<string> {
  if (reportedSize !== undefined && reportedSize > MAX_AUDIO_BYTES) {
    throw new Error('The voice message is larger than the supported 20 MB limit.');
  }

  const telegramFile = await client.getFile(fileId);
  if (!telegramFile.file_path) throw new Error('Telegram did not return a voice file path.');

  const audioResponse = await fetch(
    `https://api.telegram.org/file/bot${botToken}/${telegramFile.file_path}`,
    { signal: AbortSignal.timeout(60_000) },
  );
  if (!audioResponse.ok) {
    throw new Error(`Could not download Telegram audio (${audioResponse.status}).`);
  }

  const audio = await audioResponse.blob();
  if (audio.size > MAX_AUDIO_BYTES) {
    throw new Error('The downloaded voice message is larger than 20 MB.');
  }

  const baseUrl = optionalEnv('STT_BASE_URL', 'http://localhost:8000').replace(/\/+$/, '');
  const model = optionalEnv('STT_MODEL', 'Systran/faster-whisper-small');
  const apiKey = optionalEnv('STT_API_KEY');
  const language = optionalEnv('STT_LANGUAGE');
  const timeout = optionalNumber('STT_TIMEOUT_MS', 180_000);

  const form = new FormData();
  form.append('file', audio, `telegram-${fileId}.ogg`);
  form.append('model', model);
  form.append('response_format', 'json');
  form.append('vad_filter', 'true');
  if (language) form.append('language', language);

  const response = await fetch(`${baseUrl}/v1/audio/transcriptions`, {
    method: 'POST',
    ...(apiKey ? { headers: { Authorization: `Bearer ${apiKey}` } } : {}),
    body: form,
    signal: AbortSignal.timeout(timeout),
  });

  if (!response.ok) {
    const detail = (await response.text()).slice(0, 500);
    throw new Error(`Speech-to-text failed (${response.status}): ${detail}`);
  }

  const payload = (await response.json()) as { text?: unknown };
  if (typeof payload.text !== 'string' || !payload.text.trim()) {
    throw new Error('Speech-to-text returned no transcript.');
  }

  return payload.text.trim();
}
