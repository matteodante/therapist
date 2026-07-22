import { bash, type SandboxFactory } from '@flue/runtime';
import { Bash, InMemoryFs } from 'just-bash';

/**
 * Flue normally gives the model filesystem and bash tools. Therapist needs none
 * of them. A custom sandbox tool factory replaces that model-facing list with
 * an empty list while retaining a valid in-memory SessionEnv for Flue internals.
 *
 * Flue appends its framework-owned skill activation and task tools separately.
 * No subagents are configured, and THERAPIST.md prohibits task delegation.
 */
export function restrictedSandbox(): SandboxFactory {
  const base = bash(() => new Bash({ fs: new InMemoryFs() }));
  return {
    ...base,
    tools: () => [],
  };
}
