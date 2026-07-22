import { HindsightClient } from '@vectorize-io/hindsight-client';
import { optionalBoolean, optionalEnv } from '../shared/env.ts';
import { logError } from '../shared/log.ts';

const baseUrl = optionalEnv('HINDSIGHT_BASE_URL', 'http://localhost:8888');
const apiKey = optionalEnv('HINDSIGHT_API_KEY');
const recallBudget = optionalEnv('HINDSIGHT_RECALL_BUDGET', 'mid') as 'low' | 'mid' | 'high';
const reflectEnabled = optionalBoolean('HINDSIGHT_REFLECT_ENABLED', false);

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

export function processBankId(userKey: string): string {
  return `therapist-process-${safeKey(userKey)}`;
}

export async function ensureMemoryBanks(userKey: string): Promise<void> {
  const personal = personalBankId(userKey);
  const process = processBankId(userKey);
  const cacheKey = `${personal}:${process}`;
  if (initializedBanks.has(cacheKey)) return;

  await Promise.all([
    client.createBank(personal, {
      name: 'Therapist personal memory',
      mission:
        'Remember user-stated facts, experiences, relationships, preferences, goals, and corrections. Treat uncertainty as uncertainty. Do not create diagnoses.',
      disposition: {
        skepticism: 4,
        literalism: 4,
        empathy: 3,
      },
    }),
    client.createBank(process, {
      name: 'Therapist process memory',
      mission:
        'Remember explicitly labeled working hypotheses, intervention attempts, outcomes, open questions, and conversational preferences. Never treat hypotheses as user facts.',
      disposition: {
        skepticism: 5,
        literalism: 4,
        empathy: 3,
      },
    }),
  ]);

  initializedBanks.add(cacheKey);
}

export async function retainUserMessage(
  userKey: string,
  content: string,
  metadata: Record<string, string>,
): Promise<void> {
  try {
    await ensureMemoryBanks(userKey);
    await client.retain(personalBankId(userKey), `User: ${content}`, {
      timestamp: new Date(),
      context: 'Telegram conversation; primary evidence is the user message.',
      metadata: {
        ...metadata,
        role: 'user',
        source: 'telegram',
      },
      async: true,
    });
  } catch (error) {
    logError('memory.retain_user_failed', error, { userKey });
  }
}

export async function retainAssistantResponse(
  userKey: string,
  content: string,
): Promise<void> {
  try {
    await ensureMemoryBanks(userKey);
    await client.retain(processBankId(userKey), `Assistant response: ${content}`, {
      timestamp: new Date(),
      context:
        'Therapy process record. This is assistant-generated content and must not be treated as primary evidence about the user.',
      metadata: {
        role: 'assistant',
        source: 'telegram',
      },
      async: true,
    });
  } catch (error) {
    logError('memory.retain_assistant_failed', error, { userKey });
  }
}

export type ProcessNoteKind =
  | 'working_hypothesis'
  | 'goal'
  | 'intervention'
  | 'outcome'
  | 'preference'
  | 'open_question'
  | 'repair'
  | 'correction';

export async function retainProcessNote(
  userKey: string,
  kind: ProcessNoteKind,
  note: string,
  evidence: string,
): Promise<void> {
  await ensureMemoryBanks(userKey);
  await client.retain(
    processBankId(userKey),
    `[${kind}] ${note}\nEvidence or user confirmation: ${evidence}`,
    {
      timestamp: new Date(),
      context:
        'Structured process note. Working hypotheses remain hypotheses until the user confirms them.',
      metadata: {
        role: 'process_note',
        kind,
      },
      async: true,
    },
  );
}

export async function retainCorrection(
  userKey: string,
  incorrect: string,
  correction: string,
): Promise<void> {
  await ensureMemoryBanks(userKey);
  await client.retain(
    personalBankId(userKey),
    `USER CORRECTION: The prior information "${incorrect}" is incorrect or outdated. The user states: "${correction}".`,
    {
      timestamp: new Date(),
      context: 'Explicit user correction; prefer this over conflicting older memories.',
      metadata: {
        role: 'user',
        kind: 'correction',
      },
      async: true,
    },
  );
}

type RecalledItem = {
  text: string;
  type: string;
};

function normalizeResults(response: { results?: Array<{ text?: string; type?: string }> }): RecalledItem[] {
  return (response.results ?? [])
    .filter((item): item is { text: string; type?: string } => Boolean(item.text?.trim()))
    .map((item) => ({
      text: item.text.trim(),
      type: item.type ?? 'unknown',
    }));
}

export async function recallPersonalMemory(
  userKey: string,
  query: string,
): Promise<{ personal: RecalledItem[]; process: RecalledItem[] }> {
  await ensureMemoryBanks(userKey);

  const [personal, process] = await Promise.all([
    client.recall(personalBankId(userKey), query, {
      budget: recallBudget,
      maxTokens: 2200,
      types: ['observation', 'world', 'experience'],
    }),
    client.recall(processBankId(userKey), query, {
      budget: 'low',
      maxTokens: 1400,
      types: ['observation', 'world', 'experience'],
    }),
  ]);

  return {
    personal: normalizeResults(personal),
    process: normalizeResults(process),
  };
}

export async function reflectPersonalHistory(
  userKey: string,
  query: string,
): Promise<{ enabled: boolean; text: string }> {
  if (!reflectEnabled) {
    return {
      enabled: false,
      text: 'Reflect is disabled. Use recall_personal_memory and reason cautiously from returned evidence.',
    };
  }

  await ensureMemoryBanks(userKey);
  const response = await client.reflect(personalBankId(userKey), query, {
    budget: 'low',
    context:
      'Produce tentative cross-memory observations. Separate evidence from hypotheses and do not diagnose.',
  });

  return {
    enabled: true,
    text: response.text,
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
