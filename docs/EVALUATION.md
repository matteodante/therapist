# Evaluation strategy

## Evaluation layers

### 1. Technical

- webhook verification;
- single-user authorization;
- duplicate update handling;
- voice transcription;
- persistence;
- restart recovery;
- memory availability;
- tool boundary.

### 2. Memory

- fact precision;
- omitted facts;
- false memories;
- temporal updates;
- corrections;
- cross-language recall;
- structured/semantic separation;
- authoritative correction precedence.

### 3. Conversational competence

- empathy and collaboration;
- one-question pacing;
- guided discovery;
- uncertainty;
- repair;
- respect for listening-only requests.

### 4. Clinical fidelity

- formulation before intervention;
- alternative hypotheses;
- intervention-mechanism fit;
- outcome review;
- scope awareness;
- non-blocking high-risk response.

### 5. Longitudinal impact

- user-reported usefulness;
- functioning and goal progress;
- adverse experiences;
- emotional dependency;
- quality drift over time.

## Executable evals

Do not add inert scenario files or a project-specific eval format. Flue
recommends its `vitest-evals` tooling blueprint, retrieved with:

```bash
pnpm exec flue add tooling vitest-evals --print
```

The current Therapist agent is channel-only: its instance ID is a trusted
Telegram conversation key and its final output is delivered through a bound
Telegram tool. The official HTTP harness must not be added until the project has
a protected evaluation boundary that does not send messages to a real user.

When that boundary exists, implement the complete current Flue blueprint and
keep live-model evals separate from unit tests.

## Release gates

A model/protocol version must not become the default unless it:

- passes all critical safety scenarios;
- does not gain broad tools;
- shows acceptable memory precision;
- handles corrections;
- maintains quality in Tier 1 languages;
- is reviewed by humans on realistic multi-turn transcripts.
