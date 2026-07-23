# Data protection impact assessment screening

**Status:** preliminary screening for the planned public alpha  
**Date:** 2026-07-23  
**Owner:** Matteo Dante, individual maintainer and publisher

This is an engineering record, not a completed DPIA, legal advice, or a compliance claim. It maps
the current design against official screening criteria so a qualified adviser can decide the
applicable roles, law, and required assessment.

## Release facts

- Therapist is free, non-commercial, open-source software for one adult self-hoster.
- It supports private self-reflection and organization of user-provided thoughts; it is not intended
  for diagnosis, treatment, monitoring, or emergency use.
- The maintainer provides source and installers but does not host inference, operate user instances,
  receive telemetry, or receive application data during normal use.
- A user may run a local Ollama model or separately choose OpenAI, Anthropic, Google, OpenRouter, a
  custom PydanticAI provider, or experimental personal ChatGPT Codex OAuth.
- Telegram is optional. Local content is retained until the user corrects, forgets, exports, or
  deletes it.
- Minors, organizational deployment, patients, employees, students, paid operation, donations,
  sponsorship, and SaaS are outside this alpha.

## Processing map

| Stage | Data | Purpose | Location or recipient | Retention and control |
| --- | --- | --- | --- | --- |
| Conversation | Free text that can reveal health, relationships, beliefs, and other highly personal information | Generate a reply and maintain continuity | Local process, then the selected model provider if remote | Complete encrypted local archive until user deletion; provider terms apply externally |
| Structured memory | Exact evidence, facts, tentative hypotheses, formulation links, interventions, and session summaries | Longitudinal recall and user correction | Encrypted local SQLite | Until corrected, forgotten, or fully deleted |
| Semantic retrieval | Encrypted derived vectors and bounded candidate messages | Rank relevant local context | Local device | Rebuildable cache; affected rows removed on correction or forgetting |
| Credentials | Provider keys, Codex tokens, Telegram token and allowlisted ID | Authenticate user-selected services | Encrypted local store; service recipient on use | Local until logout or data deletion; provider terms apply |
| Telegram transport | Messages, replies, tool events, and requested memory views | Deliver the private bot conversation | Telegram plus selected model provider | Telegram and provider terms apply; local deletion cannot delete their copies |
| Public support | Synthetic reproduction and repository metadata only | Maintain the project | GitHub | GitHub terms and repository history apply |

The public channels prohibit real conversations, health information, secrets, identifiers, database
files, and exports. The application has no telemetry, advertising, analytics, automatic crash
upload, maintainer-controlled inference, or central user account.

## Screening criteria

The European Commission states that a DPIA is required when processing is likely to create a high
risk and identifies systematic evaluation, sensitive data at scale, and systematic public
monitoring as examples. The Italian Garante's mandatory list and the EDPB criteria must be evaluated
against the actual controller, deployment, users, scale, and providers.

| Criterion | Preliminary result | Reason |
| --- | --- | --- |
| Evaluation or scoring | Present | The software derives patterns, hypotheses, formulation links, and intervention history from user text, even though it prohibits diagnosis and consequential scores. |
| Automated decisions with legal or similarly significant effect | Not intended | The software does not grant, deny, rank, or decide access to services or rights. |
| Systematic monitoring | Present in the user's private archive; no maintainer monitoring | Longitudinal continuity observes conversation patterns over time. |
| Sensitive or highly personal data | Present and foreseeable | Free text can reveal health and other special-category or intimate information. |
| Large-scale processing | Not established | One local instance serves one adult; aggregate scale and external-provider processing need separate analysis. |
| Matching or combining datasets | Limited | The application combines only the user's own archive and structured memory; selected providers may have separate practices. |
| Vulnerable data subjects | Reasonably foreseeable | Adult-only intent does not remove the possibility of distress, dependency, disability, or other vulnerability. |
| Innovative technology | Present | A generative AI agent builds longitudinal, semantic, evidence-linked memory. |
| Preventing access to a service or contract | Not intended | No eligibility or service-access decision exists. |

Multiple criteria are present. If the maintainer is a controller for any in-scope processing, or the
software is deployed outside a purely personal or household activity, a full DPIA is a prudent
release requirement and may be legally required. This screening does not resolve that threshold.

## Existing controls

- explicit AI identity, adult-only intent, and no clinical, emergency, or human-monitoring claim;
- encrypted sensitive SQLite payloads and credentials with a separate local key;
- no product telemetry or maintainer-operated backend;
- bounded model context and local semantic retrieval;
- exact evidence requirements, tentative hypothesis state, correction, forgetting, export, and
  deletion controls;
- allowlisted private Telegram transport and encrypted update state;
- Telegram disclosure that cloud chats are not end-to-end encrypted and require separate deletion;
- public-report rules that prohibit personal data;
- opt-in remote providers with disclosed external data flow.

These controls reduce exposure but do not establish GDPR compliance, anonymity, confidentiality, or
provider deletion.

## Open decisions before a tagged alpha

1. Record the controller, joint-controller, processor, and independent-controller roles for the
   maintainer, self-hoster, each model provider, Telegram, GitHub, and Hugging Face.
2. Determine territorial scope and whether the personal-or-household exemption applies to each
   actual actor and flow.
3. If the maintainer is a controller, record Article 6 and Article 9 conditions, notices, data
   subject handling, retention, processor contracts, transfers, subprocessors, and breach duties.
4. Obtain and review provider DPAs, regions, transfer mechanisms, retention, training, safety
   monitoring, and deletion behavior for every configuration claimed as supported.
5. Decide whether a full DPIA is required and, if so, complete it before processing begins; consult
   the supervisory authority if high residual risk remains.
6. Re-screen before SaaS, telemetry, accounts, organizational use, minors, clinical claims, paid
   operation, donations, sponsorship, or maintainer access to user data.

## Primary sources

- [GDPR, including Articles 4, 6, 9, 25, 28, 35 and 36](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- [European Commission: when a DPIA is required](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/obligations/when-data-protection-impact-assessment-dpia-required_en)
- [Italian Garante: processing subject to mandatory DPIA](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9058979)
- [EDPB Guidelines 07/2020 on controller and processor concepts](https://www.edpb.europa.eu/documents/guideline/guidelines-072020-on-the-concepts-of-controller-and-processor-in-the-gdpr_en)
