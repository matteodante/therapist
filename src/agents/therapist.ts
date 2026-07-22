import { defineAgent } from '@flue/runtime';
import { channel, postTelegramMessage } from '../channels/telegram.ts';
import therapistInstructions from '../instructions/THERAPIST.md?raw';
import { restrictedSandbox } from '../sandboxes/restricted.ts';
import { optionalEnv } from '../shared/env.ts';
import foundationalHelping from '../skills/foundational-helping/SKILL.md' with { type: 'skill' };
import progressiveAssessment from '../skills/progressive-assessment/SKILL.md' with { type: 'skill' };
import collaborativeFormulation from '../skills/collaborative-formulation/SKILL.md' with { type: 'skill' };
import cbtAnxiety from '../skills/cbt-anxiety/SKILL.md' with { type: 'skill' };
import ruminationAndWorry from '../skills/rumination-and-worry/SKILL.md' with { type: 'skill' };
import behaviouralActivation from '../skills/behavioural-activation/SKILL.md' with { type: 'skill' };
import motivationalInterviewing from '../skills/motivational-interviewing/SKILL.md' with { type: 'skill' };
import actFlexibility from '../skills/act-psychological-flexibility/SKILL.md' with { type: 'skill' };
import sessionReview from '../skills/session-review-and-closing/SKILL.md' with { type: 'skill' };
import highRisk from '../skills/high-risk-conversation/SKILL.md' with { type: 'skill' };
import { memoryToolsFor } from '../tools/memory.ts';

const skills = [
  foundationalHelping,
  progressiveAssessment,
  collaborativeFormulation,
  cbtAnxiety,
  ruminationAndWorry,
  behaviouralActivation,
  motivationalInterviewing,
  actFlexibility,
  sessionReview,
  highRisk,
];

export default defineAgent(({ id }) => {
  const ref = channel.parseConversationKey(id);
  const userKey = String(ref.chatId);

  return {
    description:
      'A persistent, evidence-informed therapy companion for one authorized Telegram user.',
    model: optionalEnv('THERAPIST_MODEL', 'ollama/gemma4:12b'),
    instructions: therapistInstructions,
    thinkingLevel: 'high',
    sandbox: restrictedSandbox(),
    skills,
    tools: [
      ...memoryToolsFor(userKey),
      postTelegramMessage(ref, userKey),
    ],
  };
});
