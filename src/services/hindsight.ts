import { HindsightClient } from '@vectorize-io/hindsight-client';
import { optionalEnv } from '../shared/env.ts';
import { logError } from '../shared/log.ts';

const baseUrl = optionalEnv('HINDSIGHT_BASE_URL', 'http://localhost:8888');
const apiKey = optionalEnv('HINDSIGHT_API_KEY');
const recallBudget = optionalEnv('HINDSIGHT_RECALL_BUDGET', 'mid') as 'low' | 'mid' | 'high';

const client = new HindsightClient({
  baseUrl,
  ...(apiKey ? { apiKey } : {}),
  userAgent: 'therapist/0.1.0',
});

const initializedBanks = new Set<string>();

function safeKey(userKey: string): string {
  return userKey.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 100);
}

export function personalBankId(userKey: string): string {
  return `therapist-person-${safeKey(userKey)}`;
}

export async function ensureMemoryBank(
  userKey: string,
  signal?: AbortSignal,
): Promise<void> {
  const bankId = personalBankId(userKey);
  if (initializedBanks.has(bankId)) return;

  await client.createBank(bankId, {
    name: 'Therapist personal memory index',
    retainMission:
      'Index only user-stated facts, experiences, relationships, preferences, goals, and explicit corrections. Preserve uncertainty and do not create diagnoses.',
    reflectMission:
      'Treat this bank as a fallible derived index, never as the canonical source of truth.',
    dispositionSkepticism: 5,
    dispositionLiteralism: 4,
    dispositionEmpathy: 3,
    ...(signal ? { signal } : {}),
  });

  initializedBanks.add(bankId);
}

export async function retainUserMessage(
  userKey: string,
  content: string,
  metadata: Record<string, string>,
): Promise<void> {
  try {
    await ensureMemoryBank(userKey);
    const timestamp = new Date();
    await client.retain(
      personalBankId(userKey),
      `User (${timestamp.toISOString()}): ${content}`,
      {
        timestamp,
        context: 'Telegram user message; the user is the primary source.',
        metadata: {
          ...metadata,
          role: 'user',
          source: 'telegram',
        },
        documentId: 'telegram-user-messages',
        updateMode: 'append',
        tags: ['source:telegram', 'role:user'],
        async: true,
      },
    );
  } catch (error) {
    logError('memory.retain_user_failed', error, { userKey });
  }
}

export async function indexCorrection(
  userKey: string,
  incorrect: string,
  correction: string,
  signal?: AbortSignal,
): Promise<void> {
  try {
    await ensureMemoryBank(userKey, signal);
    await client.retain(
      personalBankId(userKey),
      `User correction: "${incorrect}" is incorrect or outdated. Current information: "${correction}".`,
      {
        timestamp: new Date(),
        context: 'Explicit user correction; prefer this over conflicting older memories.',
        metadata: { role: 'user', kind: 'correction' },
        documentId: 'user-corrections',
        updateMode: 'append',
        tags: ['role:user', 'kind:correction'],
        async: true,
        ...(signal ? { signal } : {}),
      },
    );
  } catch (error) {
    logError('memory.retain_correction_failed', error, { userKey });
  }
}

export type RecalledItem = {
  text: string;
  type: string;
  context: string;
  documentId: string;
  mentionedAt: string;
};

export async function recallPersonalMemory(
  userKey: string,
  query: string,
  signal?: AbortSignal,
): Promise<RecalledItem[]> {
  await ensureMemoryBank(userKey, signal);
  const response = await client.recall(personalBankId(userKey), query, {
    budget: recallBudget,
    maxTokens: 2200,
    types: ['world', 'experience'],
    ...(signal ? { signal } : {}),
  });

  return response.results.flatMap((item) => {
    const text = item.text.trim();
    return text
      ? [{
          text,
          type: item.type ?? 'unknown',
          context: item.context ?? '',
          documentId: item.document_id ?? '',
          mentionedAt: item.mentioned_at ?? '',
        }]
      : [];
  });
}

export async function clearPersonalMemoryIndex(
  userKey: string,
): Promise<{ failedDocuments: number }> {
  const bankId = personalBankId(userKey);
  const results = await Promise.allSettled([
    client.deleteDocument(bankId, 'telegram-user-messages'),
    client.deleteDocument(bankId, 'user-corrections'),
  ]);

  for (const result of results) {
    if (result.status === 'rejected') {
      logError('memory.delete_document_failed', result.reason, { userKey });
    }
  }

  return {
    failedDocuments: results.filter((result) => result.status === 'rejected').length,
  };
}

export async function hindsightHealth(): Promise<Record<string, unknown>> {
  const version = await client.getVersion({ signal: AbortSignal.timeout(5000) });
  return {
    ok: true,
    apiVersion: version.api_version,
    features: version.features,
  };
}
