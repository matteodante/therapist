import { describe, expect, it } from 'vitest';
import { personalBankId } from '../src/services/hindsight.ts';

describe('memory bank IDs', () => {
  it('creates a user-scoped personal index', () => {
    expect(personalBankId('123')).toBe('therapist-person-123');
  });

  it('sanitizes untrusted identifiers', () => {
    expect(personalBankId('../abc')).toBe('therapist-person-___abc');
  });
});
