# Public alpha readiness record — 2026-08-04

## Decision

**Local `v0.2.0` candidate:** built, installed, and offline-verified  
**Tagged GitHub prerelease:** **NO-GO**  
**Public installer switch to `v0.2.0`:** **NO-GO**

The implementation, offline suite, dependency audit, package build, isolated wheel installation,
and local user-tool installation pass. Publication remains blocked by two mandatory gates: the live
Codex suite must be repeated on the exact final protocol hash after the personal Plus usage limit
resets, and the private Telegram smoke must run on the candidate. This record is engineering
evidence, not clinical validation, legal approval, or safety certification.

## Candidate

- Package version: `0.2.0`; intended immutable tag: `v0.2.0`.
- Final local protocol root SHA-256:
  `2e5a039d45f4ca2879ac8fc0ba4352ac905d8bdfe3bd236c4ceda473ae902560`.
- Free, non-commercial, adult-only, single-user self-hosted alpha.
- Supported release claim: local CLI and one private Telegram bot using a personal ChatGPT
  Plus/Pro account through the experimental `codex:` OAuth provider.
- Mandatory boundary: AI for self-reflection, not therapy, diagnosis, treatment, medical advice,
  emergency care, clinical validation, or human monitoring.

The installers are prepared to select `v0.2.0`, but that tag does not exist and `main` has not been
pushed. The published `main` installer therefore still selects the prior public alpha until the
mandatory gates pass and the release is published atomically.

## Local gates on 2026-08-04

| Gate | Result |
| --- | --- |
| Locked environment sync | Passed; 108 packages resolved |
| Ruff formatting and lint | Passed |
| `ty` on `src/therapist` | Passed |
| Offline deterministic suite | 192 passed, 5 live tests deselected |
| Total coverage | 76%; configured 75% floor passed |
| Protocol validation | Passed; 15 skills, all root/skill/reference hashes valid |
| Protocol reviewers | 0; no clinical review claimed |
| POSIX installer syntax | Passed |
| PowerShell installer syntax | Not run locally because `pwsh` is unavailable; Windows CI remains required |
| Locked dependency audit | No known vulnerabilities or adverse project statuses in 107 packages |
| Source distribution and wheel | Built successfully |
| Twine metadata | Passed for both artifacts |
| Wheel contents | All 15 skills, all source bases, manifest, root protocol, and license present |
| Fresh isolated wheel installation | Passed `protocol validate`, `doctor`, and `auth status` |
| Local user-tool installation | `therapist-cli v0.2.0` installed; state and model cache preserved |
| Local doctor | Passed; semantic model installed; Telegram not configured |
| Local semantic-model verification | Passed; 12 files, 1,024 dimensions, local inference successful |
| Codex OAuth | Logged in; encrypted credential available; automatic refresh reported |

Local wheel checksum:

```text
c0ea39ccedbe9f4c3df3ae38f1258d23bb97c403ce1a65562c4bee6d735609af  therapist_cli-0.2.0-py3-none-any.whl
```

This is a local pre-release artifact, not an authoritative release attachment. The source archive
contains this readiness record, so its digest is deliberately not embedded in the archive itself.
The manual GitHub candidate workflow must rebuild from the final pushed commit and produce the
external `SHA256SUMS`, SBOM, provenance, and attestations.

## Live Codex evidence

All live datasets use synthetic content and the experimental personal ChatGPT Codex path with
`gpt-5.6-sol`.

- The rewritten conversational pack passed 20/20 role-plays. The same harness against the extracted
  previous pack revision passed 19/20. Each is one stochastic baseline; this supports comparison but
  is not a statistical or clinical claim.
- The bilingual safety dataset passed all 10 scenarios for three repeats, including the corrected
  asynchronous semantic judge: 30/30 scenario-runs.
- The longitudinal-memory dataset passed after making its synthetic hypothesis flow unambiguous. It
  verified agent-hypothesis provenance and fit, encrypted persistence, paired tool history/export,
  consolidation, local semantic retrieval, and continuity after a simulated four months.
- Those complete results preceded the final two protocol refinements. On the final hash,
  ROLEPLAY-20 passed 3/3 and the next full role-play run completed and wrote passing artifacts for
  ROLEPLAY-01 through ROLEPLAY-12. The provider then returned `usage_limit_reached` before the
  remaining cases and judge calls could complete.

The account reports a reset at `2026-08-10T10:49:53+02:00`. After reset, rerun on the exact final
candidate:

```bash
THERA_RUN_CONVERSATION_EVALS=1 THERA_EVAL_MODEL=codex:gpt-5.6-sol \
  uv run pytest tests/test_live_conversational_roleplays.py -m live

THERA_RUN_CODEX_EVALS=1 \
  uv run pytest tests/test_live_codex_memory.py -m live

THERA_RUN_CODEX_SAFETY_EVALS=1 THERA_CODEX_SAFETY_EVAL_REPEAT=3 \
  uv run pytest tests/test_live_codex_safety.py -m live
```

Do not combine the partial final run with an earlier hash and call it a full pass.

## Remaining publication gates

1. Rerun all three live Codex gates above on the exact final commit after the usage limit resets.
2. Configure an allowlisted private Telegram bot and run the candidate smoke without logging secrets
   or personal content.
3. Push the final candidate to `main`; require CI and CodeQL green on that exact commit.
4. Run and verify the manual `Release candidate` workflow, artifact checksums, SBOM, provenance, and
   attestations.
5. Create and verify the signed immutable tag, publish the GitHub prerelease, and only then test the
   documented public installer path.

Until those gates pass, do not create `v0.2.0`, publish a prerelease, or push an installer change
that points the public bootstrap at a nonexistent tag.
