import { describe, expect, it } from 'vitest';
import { personalBankId, processBankId } from '../src/services/hindsight.ts';

describe('memory bank IDs', () => {
  it('separates personal facts and process notes', () => {
    expect(personalBankId('123')).toBe('therapist-person-123');
    expect(processBankId('123')).toBe('therapist-process-123');
  });

  it('sanitizes untrusted identifiers', () => {
    expect(personalBankId('../abc')).toBe('therapist-person-___abc');
  });
});
