import { defineTool } from '@flue/runtime';
import * as v from 'valibot';
import {
  correctMemory,
  readMemoryVault,
  recordJourneyNote,
  rememberUserContext,
} from '../storage/memory-vault.ts';

const recall = defineTool({
  name: 'read_therapy_memory',
  description:
    'Read the complete concise therapy memory. SELF contains user-stated context; JOURNEY contains collaborative process notes.',
  output: v.object({
    self: v.string(),
    journey: v.string(),
  }),
  run() {
    return readMemoryVault();
  },
});

const userContext = defineTool({
  name: 'remember_user_context',
  description:
    'Remember concise context explicitly stated or confirmed by the user. Never store an assistant inference with this tool.',
  input: v.object({
    note: v.pipe(v.string(), v.minLength(3), v.maxLength(1200)),
    evidence: v.pipe(v.string(), v.minLength(3), v.maxLength(1000)),
  }),
  output: v.object({ stored: v.boolean() }),
  run({ input }) {
    rememberUserContext(input.note, input.evidence);
    return { stored: true };
  },
});

const journeyNote = defineTool({
  name: 'record_therapy_process_note',
  description:
    'Record one useful collaborative therapy-process note with user evidence. Working hypotheses must remain explicitly tentative.',
  input: v.object({
    kind: v.picklist([
      'working_hypothesis',
      'goal',
      'experiment',
      'outcome',
      'open_thread',
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
    recordJourneyNote(input.kind, input.note, input.evidence);
    return { stored: true };
  },
});

const correction = defineTool({
  name: 'correct_therapy_memory',
  description:
    'Replace incorrect text in an existing memory bullet. Read memory first and pass the exact incorrect excerpt. If no match is found, use the appropriate memory-write tool.',
  input: v.object({
    incorrect: v.pipe(v.string(), v.minLength(1), v.maxLength(1000)),
    correction: v.pipe(v.string(), v.minLength(1), v.maxLength(1000)),
  }),
  output: v.object({
    updated: v.boolean(),
    file: v.nullable(v.picklist(['self', 'journey'])),
  }),
  run({ input }) {
    return correctMemory(input.incorrect, input.correction);
  },
});

export const memoryTools = [recall, userContext, journeyNote, correction];
