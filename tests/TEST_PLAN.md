# Structured test plan

All people, events, projects, and dates below are synthetic. Pydantic Evals executes the written
YAML datasets in `tests/cases/`; pytest only provides the outer test runner and storage-level
contracts.

| ID | Level | Scenario | Expected result |
| --- | --- | --- | --- |
| LM-001 | Deterministic | Return after four months and restart the process | Relevant event and tentative pattern return with evidence and distinct statuses |
| LM-002 | Deterministic | Correct a stored location, wait six months, and restart | Corrected value wins; superseded value and source excerpt stay out of working context |
| LM-003 | Deterministic | Forget one event, wait nine months, and restart | Event stays out of active context; export retains only an `archived` audit record |
| LM-004 | Deterministic | Build hundreds of sessions and memory items | Working context remains capped at 30 confirmed items, 10 hypotheses, 3 sessions, and 5 excerpts |
| LM-005 | Deterministic | Inspect SQLite after longitudinal use | User messages, observations, summaries, and formulation are not stored as plaintext |
| SKILL-001..005 | Deterministic Pydantic Evals | Audit each versioned therapeutic skill | Required workflow, consent, review, and boundary clauses remain present |
| SKILL-006 | Deterministic Pydantic Evals | Audit the root skill router | One intervention at a time; uncertainty routes back to formulation |
| LIVE-001 | Real provider + LLM judge | Complete a synthetic avoidance case, consolidate, restart, and return after four months | Storage gates pass and the transcript demonstrates listening, shared formulation, pacing, a small agreed intervention, outcome review, and accurate continuity |

Run deterministic tests on every change:

```bash
uv run pytest -m "not live"
```

Run the real-provider case explicitly when credentials and network access are available:

```bash
THERA_RUN_LIVE_TESTS=1 OPENAI_API_KEY=... uv run pytest -m live
```

The live test intentionally avoids assertions about exact prose because model wording is
non-deterministic. Pydantic Evals verifies observable persistence and continuity contracts instead.
