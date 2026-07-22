import { describe, expect, it } from 'vitest';
import { splitTelegramText } from '../src/shared/telegram.ts';

describe('splitTelegramText', () => {
  it('keeps short text intact', () => {
    expect(splitTelegramText('hello')).toEqual(['hello']);
  });

  it('splits long text within the limit', () => {
    const chunks = splitTelegramText('word '.repeat(2000), 400);
    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.every((chunk) => chunk.length <= 400)).toBe(true);
  });
});
