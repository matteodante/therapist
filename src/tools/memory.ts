import { defineTool } from '@flue/runtime';
import * as v from 'valibot';
import { indexCorrection, recallPersonalMemory } from '../services/hindsight.ts';
import {
  recallStructuredMemory,
  recordStructuredMemory,
} from '../storage/app-db.ts';

const recalledItem = v.object({
  text: v.string(),
  type: v.string(),
  context: v.string(),
  documentId: v.string(),
  mentionedAt: v.string(),
});

const structuredItem = v.object({
  kind: v.string(),
  note: v.string(),
  evidence: v.string(),
  createdAt: v.string(),
});

export function memoryToolsFor(userKey: string) {
  const recall = defineTool({
    name: 'recall_personal_memory',
    description:
      'Recall structured user-confirmed records and a fallible semantic index of user messages. Prefer structured records when sources conflict.',
    input: v.object({
      query: v.pipe(
        v.string(),
        v.minLength(3),
        v.maxLength(800),
        v.description('A focused query based on the current user message.'),
      ),
    }),
    output: v.object({
      structured: v.array(structuredItem),
      semantic: v.array(recalledItem),
    }),
    async run({ input, signal }) {
      const structured = recallStructuredMemory(userKey, input.query);
      const semantic = await recallPersonalMemory(userKey, input.query, signal);
      return { structured, semantic };
    },
  });

  const processNote = defineTool({
    name: 'record_therapy_process_note',
    description:
      'Record one concise structured note only after user evidence or confirmation. Working hypotheses must remain explicitly tentative.',
    input: v.object({
      kind: v.picklist([
        'working_hypothesis',
        'goal',
        'intervention',
        'outcome',
        'preference',
        'open_question',
        'repair',
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
    run({ input }) {
      recordStructuredMemory(userKey, input.kind, input.note, input.evidence);
      return { stored: true };
    },
  });

  const correction = defineTool({
    name: 'record_memory_correction',
    description:
      'Record an explicit user correction. The structured correction is authoritative; the semantic index remains derived and fallible.',
    input: v.object({
      incorrect: v.pipe(v.string(), v.minLength(1), v.maxLength(1000)),
      correction: v.pipe(v.string(), v.minLength(1), v.maxLength(1000)),
    }),
    output: v.object({ stored: v.boolean() }),
    async run({ input, signal }) {
      recordStructuredMemory(
        userKey,
        'correction',
        input.correction,
        `Supersedes: ${input.incorrect}`,
      );
      await indexCorrection(userKey, input.incorrect, input.correction, signal);
      return { stored: true };
    },
  });

  return [recall, processNote, correction];
}
