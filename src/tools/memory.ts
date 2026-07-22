import { defineTool } from '@flue/runtime';
import * as v from 'valibot';
import {
  recallPersonalMemory,
  reflectPersonalHistory,
  retainCorrection,
  retainProcessNote,
} from '../services/hindsight.ts';

const recalledItem = v.object({
  text: v.string(),
  type: v.string(),
});

export function memoryToolsFor(userKey: string) {
  const recall = defineTool({
    name: 'recall_personal_memory',
    description:
      'Recall relevant user-stated history and separately labeled process notes. Use before substantive replies when prior context may matter. Treat results as fallible context, not unquestionable fact.',
    input: v.object({
      query: v.pipe(
        v.string(),
        v.minLength(3),
        v.maxLength(800),
        v.description('A focused query based on the current user message.'),
      ),
    }),
    output: v.object({
      personal: v.array(recalledItem),
      process: v.array(recalledItem),
    }),
    async run({ input, signal }) {
      return recallPersonalMemory(userKey, input.query, signal);
    },
  });

  const reflect = defineTool({
    name: 'reflect_on_personal_history',
    description:
      'Generate a tentative synthesis across personal memories. Use sparingly, only when cross-session pattern synthesis is necessary. The result is a hypothesis, never a diagnosis.',
    input: v.object({
      query: v.pipe(v.string(), v.minLength(3), v.maxLength(800)),
    }),
    output: v.object({
      enabled: v.boolean(),
      text: v.string(),
    }),
    async run({ input, signal }) {
      return reflectPersonalHistory(userKey, input.query, signal);
    },
  });

  const processNote = defineTool({
    name: 'record_therapy_process_note',
    description:
      'Record a concise therapy-process note after the user has provided evidence or confirmation. Use for goals, outcomes, open questions, preferences, repairs, and explicitly tentative working hypotheses.',
    input: v.object({
      kind: v.picklist([
        'working_hypothesis',
        'goal',
        'intervention',
        'outcome',
        'preference',
        'open_question',
        'repair',
        'correction',
      ]),
      note: v.pipe(v.string(), v.minLength(3), v.maxLength(1200)),
      evidence: v.pipe(
        v.string(),
        v.minLength(3),
        v.maxLength(1000),
        v.description('User statement or outcome supporting the note.'),
      ),
    }),
    output: v.object({ stored: v.boolean() }),
    async run({ input, signal }) {
      await retainProcessNote(userKey, input.kind, input.note, input.evidence, signal);
      return { stored: true };
    },
  });

  const correction = defineTool({
    name: 'record_memory_correction',
    description:
      'Record an explicit user correction to a prior memory. Use only when the user states that something remembered is wrong, outdated, or should be replaced.',
    input: v.object({
      incorrect: v.pipe(v.string(), v.minLength(1), v.maxLength(1000)),
      correction: v.pipe(v.string(), v.minLength(1), v.maxLength(1000)),
    }),
    output: v.object({ stored: v.boolean() }),
    async run({ input, signal }) {
      await retainCorrection(userKey, input.incorrect, input.correction, signal);
      return { stored: true };
    },
  });

  return [recall, reflect, processNote, correction];
}
