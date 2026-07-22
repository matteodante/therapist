import {
  mkdirSync,
  readFileSync,
  renameSync,
  writeFileSync,
} from 'node:fs';
import { resolve } from 'node:path';
import { optionalEnv } from '../shared/env.ts';

const defaultRoot = resolve(optionalEnv('THERAPIST_MEMORY_PATH', './data/memory'));

const templates = {
  self: `# Self

Only user-stated or user-confirmed context belongs here. Keep it concise and
replace outdated information instead of preserving contradictions.

## Remembered context
`,
  journey: `# Journey

Collaborative therapy-process notes belong here. Hypotheses are tentative and
must remain separate from user-stated facts in SELF.md.

## Goals

## Working hypotheses

## Experiments

## Outcomes

## Open threads

## Repairs
`,
} as const;

type MemoryFile = keyof typeof templates;
export type JourneyKind =
  | 'goal'
  | 'working_hypothesis'
  | 'experiment'
  | 'outcome'
  | 'open_thread'
  | 'repair';

const journeyHeadings: Record<JourneyKind, string> = {
  goal: 'Goals',
  working_hypothesis: 'Working hypotheses',
  experiment: 'Experiments',
  outcome: 'Outcomes',
  open_thread: 'Open threads',
  repair: 'Repairs',
};

function pathFor(file: MemoryFile, root: string): string {
  return resolve(root, file === 'self' ? 'SELF.md' : 'JOURNEY.md');
}

function ensureVault(root = defaultRoot): void {
  mkdirSync(root, { recursive: true, mode: 0o700 });
  for (const file of ['self', 'journey'] as const) {
    try {
      writeFileSync(pathFor(file, root), templates[file], {
        encoding: 'utf8',
        flag: 'wx',
        mode: 0o600,
      });
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error;
    }
  }
}

function clean(value: string): string {
  return value.replace(/\s+/g, ' ').trim();
}

function requiredText(value: string, name: string): string {
  const cleaned = clean(value);
  if (!cleaned) throw new Error(`${name} cannot be blank.`);
  return cleaned;
}

function atomicWrite(file: MemoryFile, content: string, root = defaultRoot): void {
  const destination = pathFor(file, root);
  const temporary = `${destination}.${process.pid}.tmp`;
  writeFileSync(temporary, content, { encoding: 'utf8', mode: 0o600 });
  renameSync(temporary, destination);
}

function entry(note: string, evidence: string): string {
  return `- ${requiredText(note, 'Note')} _(Evidence: ${requiredText(evidence, 'Evidence')}; recorded ${new Date().toISOString().slice(0, 10)})_`;
}

export function readMemoryVault(root = defaultRoot): { self: string; journey: string } {
  ensureVault(root);
  // ponytail: read both concise notes whole; add an index only after measured context growth.
  return {
    self: readFileSync(pathFor('self', root), 'utf8'),
    journey: readFileSync(pathFor('journey', root), 'utf8'),
  };
}

export function rememberUserContext(
  note: string,
  evidence: string,
  root = defaultRoot,
): void {
  const memory = readMemoryVault(root).self.trimEnd();
  atomicWrite('self', `${memory}\n${entry(note, evidence)}\n`, root);
}

export function recordJourneyNote(
  kind: JourneyKind,
  note: string,
  evidence: string,
  root = defaultRoot,
): void {
  const memory = readMemoryVault(root).journey;
  const heading = `## ${journeyHeadings[kind]}`;
  const start = memory.indexOf(heading);
  if (start === -1) throw new Error(`JOURNEY.md is missing the ${heading} section.`);
  const next = memory.indexOf('\n## ', start + heading.length);
  const at = next === -1 ? memory.length : next;
  const updated = `${memory.slice(0, at).trimEnd()}\n${entry(note, evidence)}\n\n${memory.slice(at).trimStart()}`;
  atomicWrite('journey', updated, root);
}

export function correctMemory(
  incorrect: string,
  correction: string,
  root = defaultRoot,
): { updated: boolean; file: MemoryFile | null } {
  ensureVault(root);
  const target = requiredText(incorrect, 'Incorrect text');
  const replacement = requiredText(correction, 'Correction');
  for (const file of ['self', 'journey'] as const) {
    const lines = readFileSync(pathFor(file, root), 'utf8').split('\n');
    const index = lines.findIndex((line) => line.startsWith('- ') && line.includes(target));
    if (index === -1) continue;
    lines[index] = lines[index]!.replace(target, replacement);
    atomicWrite(file, lines.join('\n'), root);
    return { updated: true, file };
  }
  return { updated: false, file: null };
}

export function resetMemoryVault(root = defaultRoot): number {
  const memory = readMemoryVault(root);
  const removed = `${memory.self}\n${memory.journey}`
    .split('\n')
    .filter((line) => line.startsWith('- ')).length;
  atomicWrite('self', templates.self, root);
  atomicWrite('journey', templates.journey, root);
  return removed;
}
