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
- personal/process separation.

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

## Current eval assets

`evals/scenarios/` contains starter cases. They are specifications for human or
automated review, not proof of clinical efficacy.

## Release gates

A model/protocol version must not become the default unless it:

- passes all critical safety scenarios;
- does not gain broad tools;
- shows acceptable memory precision;
- handles corrections;
- maintains quality in Tier 1 languages;
- is reviewed by humans on realistic multi-turn transcripts.
