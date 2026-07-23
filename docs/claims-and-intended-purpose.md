# Claims and intended purpose

This document is the proposed release baseline for the non-commercial public alpha. It records
product intent and claim boundaries; it is not legal advice, regulatory approval, or a medical-device
classification.

## Public claim

> **An open-source AI agent for reflection, not code.**

Supporting line:

> Local-first conversations and user-controlled memory for self-reflection and mental wellbeing.

Mandatory nearby limitation:

> Experimental and not clinically validated. It is not therapy, diagnosis, medical advice, or
> emergency care; no human monitors conversations. AI output can be wrong. Your selected model
> provider and, if enabled, Telegram receive the content needed to provide their services.

## Intended purpose

Therapist is intended to support adult self-reflection and organization of user-provided thoughts.
It is not intended for diagnosis, prevention, monitoring, prediction, prognosis, treatment, or
alleviation of any disease, disorder, injury, or disability.

## Initial release assumptions

- source and installers are distributed without charge and outside commercial activity;
- one adult operates one private self-hosted instance;
- there is no hosted service, telemetry, advertising, analytics, paid support, or
  maintainer-controlled inference;
- the user separately selects and contracts with any remote model provider and Telegram;
- the maintainer does not receive application data unless the user deliberately submits it;
- institutional, employer, school, clinician, patient, client, and minor use are outside scope;
- no efficacy, safety, clinical equivalence, compliance, or regulatory-approval claim is made.

## Supported factual claims

Public material may describe behavior verified by code and tests:

- open-source under AGPL-3.0-or-later;
- self-hosted and local-first, with explicit remote-provider and Telegram data flows;
- encrypted sensitive SQLite payloads and a separate local key;
- user inspection, correction, forgetting, export, and deletion controls;
- evidence-linked distinction between user-supported claims and agent hypotheses;
- bounded longitudinal context and local semantic retrieval;
- Italian and English conversation through terminal and private Telegram transports;
- experimental protocol and opt-in real-provider evaluations.

## Prohibited claims

Do not describe the project as:

- therapy, psychotherapy, treatment, clinical care, or a substitute for a professional;
- a psychologist, psychotherapist, clinician, medical device, or emergency service;
- able to diagnose, assess risk clinically, prescribe, monitor, keep a user safe, or contact help;
- proven safe, effective, confidential, anonymous, GDPR compliant, medically approved, or validated;
- equivalent or superior to therapy, a clinician, or an evidence-based treatment;
- suitable for minors, patients, institutions, workplaces, schools, or high-acuity care;
- fully local or private when a remote model or Telegram is configured.

Internal implementation terms such as formulation, intervention records, and protocol skills describe
software structures. They are not benefit, efficacy, or clinical-use claims.

## Surfaces covered by this inventory

The claim and limitation must remain consistent in:

- repository description, topics, README, package metadata, release notes, and future website;
- installers, setup, consent, CLI help, Telegram bot description, commands, and privacy view;
- screenshots, demonstrations, examples, issue templates, and contributor documentation;
- protocol documentation and model-facing instructions where they affect visible behavior.

## Release gate and change triggers

The first public release still requires a written EU medical-device classification assessment by
qualified counsel or a regulatory specialist. Reassess this document before adding symptom scales,
named-condition pathways, medication advice, clinical dashboards, institutional deployment,
efficacy claims, minors, hosted operation, paid support, sponsorship tied to the product, or
maintainer access to user data.
