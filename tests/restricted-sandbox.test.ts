import { describe, expect, it } from 'vitest';
import { restrictedSandbox } from '../src/sandboxes/restricted.ts';

describe('restricted sandbox', () => {
  it('exposes no sandbox-owned model tools', () => {
    const sandbox = restrictedSandbox();
    expect(sandbox.tools).toBeTypeOf('function');
    expect(sandbox.tools?.({} as never, { subagents: {} })).toEqual([]);
  });
});
