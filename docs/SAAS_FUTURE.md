# Future SaaS product

The hosted edition is a later product phase. It must remain compatible with the
self-hosted edition and avoid data lock-in.

## Product promise

```text
Self-hosted → maximum control
SaaS        → maximum convenience
```

## Required architecture changes

- Postgres persistence for Flue;
- one active owner per agent instance;
- tenant-scoped Hindsight banks;
- authenticated first-party API;
- managed webhook routing;
- object storage for encrypted exports;
- key management;
- observability without message content;
- deletion and export workers;
- regional deployment strategy.

## Portability

A user must be able to export:

- canonical transcript;
- personal memories;
- process notes;
- formulations;
- goals;
- interventions and outcomes;
- protocol versions;
- preferences.

The same package must be importable into self-hosted or SaaS deployments.

## Before launch

- clinical governance;
- security assessment;
- privacy impact assessment;
- terms and intended-purpose review;
- abuse and crisis policy;
- retention policy;
- support operations;
- regulatory analysis;
- longitudinal evaluation.
