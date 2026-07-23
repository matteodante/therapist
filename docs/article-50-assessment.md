# EU AI Act Article 50 assessment record

**Status:** open release gate; qualified role and marking decision required  
**Date:** 2026-07-23  
**Scope:** free, non-commercial, adult-only public alpha published by Matteo Dante

This record applies the European Commission's final Article 50 guidance to the actual alpha. It is
not legal advice or a compliance determination.

## Facts that are already clear

Therapist is an AI system designed for a direct two-way exchange with natural persons. It produces
textual conversation through a terminal or Telegram and is distributed under the Therapist name.
It uses third-party or local models but adds its own instructions, memory, tools, validation, storage,
and user interface.

The current product already tells a user clearly, before conversation, that:

- Therapist is an AI;
- it is not therapy, diagnosis, medical advice, emergency care, or human monitoring;
- output can be wrong;
- the selected remote provider and Telegram receive required content.

This disclosure appears in the README, guided setup, terminal consent, Telegram consent and status
surfaces. It should remain clear, distinguishable, accessible, and present from the start of the
first interaction.

## Unresolved role and obligation

The Commission defines a provider as a person or body that develops or has an AI system developed
and places it on the EU market or puts it into service under its own name or trademark. On the known
facts, publishing a composed agent under the Therapist name creates a material risk that the
publisher is a provider rather than only a distributor of upstream models. A qualified specialist
must record that role analysis for this open-source, non-commercial distribution.

Article 2(12) does not create a general Article 50 safe harbor for free and open-source AI: its
exclusion expressly does not cover systems that fall under Article 50. Free distribution and an
open-source license therefore do not, by themselves, close this assessment.

If Therapist is a provider:

- Article 50(1) interaction disclosure applies unless the AI nature is obvious; relying on that
  exception is unnecessary because explicit disclosure already exists.
- Article 50(2) may require generative text output to carry effective, reliable, robust,
  interoperable, machine-readable marks. Conversational replies are not source code, and no such
  marking is implemented today.

The Commission's final guidance says Article 50 applies from 2 August 2026. Systems placed on the
market before then receive a limited grace period only for Article 50(2) marking, until
2 December 2026. The project will not treat early publication as a substitute for a role and
implementation decision.

## Go/no-go record

Before a tagged public alpha, record one of these outcomes with the responsible specialist, source,
date, scope, and rationale:

1. Therapist is a provider and implements an adequate Article 50(2) marking method plus the existing
   Article 50(1) disclosure;
2. Therapist is a provider but a documented exemption or transition rule applies to the exact
   release, with its end date and follow-up owner;
3. Therapist is not the relevant provider for a stated legal reason, and the actual provider and
   downstream obligations are identified.

Current result: **no outcome has been approved; release remains blocked on this gate.**

Any technical implementation must follow the Commission's final guidance and current Code of
Practice, including output-format interoperability and accessibility. Do not invent a custom marker
and call it compliant without review.

## Primary sources

- [Regulation (EU) 2024/1689, especially Articles 3 and 50](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [European Commission final Article 50 guidelines, 20 July 2026](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems)
- [European Commission Article 50 questions and answers](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)
- [Code of Practice on Transparency of AI-generated Content](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)
