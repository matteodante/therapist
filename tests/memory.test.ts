import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import {
  correctMemory,
  readMemoryVault,
  recordJourneyNote,
  rememberUserContext,
  resetMemoryVault,
} from '../src/storage/memory-vault.ts';

const root = mkdtempSync(join(tmpdir(), 'therapist-memory-'));
afterAll(() => rmSync(root, { recursive: true }));

describe('Markdown memory vault', () => {
  it('keeps user context separate from therapy process notes', () => {
    rememberUserContext('Lives in Rome', 'The user stated this directly', root);
    recordJourneyNote('goal', 'Sleep more consistently', 'The user chose this goal', root);

    const memory = readMemoryVault(root);
    expect(memory.self).toContain('Lives in Rome');
    expect(memory.self).not.toContain('Sleep more consistently');
    expect(memory.journey).toContain('## Goals\n- Sleep more consistently');
  });

  it('corrects exact memory text and resets the vault', () => {
    expect(correctMemory('Rome', 'Milan', root)).toEqual({ updated: true, file: 'self' });
    expect(readMemoryVault(root).self).toContain('Lives in Milan');
    expect(() => correctMemory('   ', 'Unsafe replacement', root)).toThrow();
    expect(resetMemoryVault(root)).toBe(2);
    expect(readMemoryVault(root).self).not.toContain('Lives in Milan');
  });
});
