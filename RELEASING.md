# Releasing

Therapist releases are maintainer-controlled snapshots of an experimental, non-commercial,
adult-only project. A release is not clinical validation, regulatory approval, or evidence that the
software is safe or effective for mental-health treatment.

The first release is a controlled public alpha for technical contributors and informed adult
self-hosters. Do not promote it broadly, publish it to PyPI, offer hosted operation, or describe it
as therapy or treatment.

## Release authority

The maintainer named in [GOVERNANCE.md](GOVERNANCE.md) makes the final go/no-go decision, writes the
release notes, signs the tag, publishes the GitHub prerelease, and coordinates withdrawal when
needed. A failed mandatory gate cannot be waived silently; record the owner, reason, scope, and
expiry of any exception in the release notes.

## Mandatory gates

Before creating a tag, link durable evidence for every item below in the release issue or notes:

- the intended purpose, public claim, initial operator, users, jurisdictions, and non-commercial
  distribution assumptions are approved;
- qualified EU counsel or a regulatory specialist has recorded the medical-device classification
  assessment;
- the GDPR role map, legal-basis and Article 9 analysis, provider/transfer review, and DPIA screening
  match the actual release;
- the EU AI Act Article 50 machine-readable marking decision is recorded and implemented where
  required;
- the Code of Conduct and reporting routes accurately state that there is no confidential
  project-specific conduct inbox;
- the candidate was pushed directly to `main` only after local checks, and the resulting required CI
  and CodeQL runs are green;
- private vulnerability reporting, dependency alerts, secret scanning, push protection, and CodeQL
  are enabled;
- the latest OpenSSF Scorecard result has been reviewed as a diagnostic, with accepted
  single-maintainer findings recorded rather than represented as certification;
- current provider terms and safety policies have been reviewed;
- the bilingual safety suite has passed three repeats, with model, provider, protocol commit,
  locale, results, and residual failures recorded;
- deterministic tests, lint, formatting, protocol validation, installer syntax, wheel installation,
  packaging metadata, dependency audit, and the configured real-provider memory evaluation pass;
- public claims, runtime consent, privacy notice, support guidance, examples, and release notes remain
  consistent with [docs/claims-and-intended-purpose.md](docs/claims-and-intended-purpose.md);
- license, protocol-source references, bundled embedding-model license, and generated artifacts have
  been reviewed;
- the package version, tag, installer channel, supported revision, and rollback target are explicit.

If any legal, privacy, AI Act, safety, or conduct gate is open, stop. A green CI run is not authority
to release.

Use [docs/compliance-assessment-brief.md](docs/compliance-assessment-brief.md) for the external
review, [docs/dpia-screening.md](docs/dpia-screening.md) for the preliminary data-protection record,
and [docs/article-50-assessment.md](docs/article-50-assessment.md) for the open transparency decision.
Use [docs/release-readiness-2026-07-23.md](docs/release-readiness-2026-07-23.md) as the current
engineering evidence and open-blocker record.

## Accepted alpha governance risks

The individual publisher has explicitly chosen direct pushes to `main`, no required pull-request
review, no second administrator or recovery owner, and no private project-specific conduct inbox for
this phase. These are documented single-maintainer limitations, not waived security, privacy, or
regulatory gates.

Before every direct push, run the proportionate local checks. After the push, inspect the exact
commit's GitHub CI and CodeQL results before tagging. Never describe the release as independently
reviewed, protected by multi-person governance, continuously recoverable, or able to accept
confidential conduct cases. Reassess these constraints before broader promotion or material growth.

## Version and tag policy

- Use Semantic Versioning for Git tags and PEP 440-compatible package versions.
- Versions below `1.0.0` are experimental and may change incompatibly.
- Mark every alpha GitHub release as a prerelease.
- The tag, package version, release title, and release notes must identify the same version.
- Create an annotated, cryptographically signed tag from a clean, current `main`.
- Never move or reuse a published tag. Fix forward with a new version.
- Only the latest documented alpha revision is supported unless the release notes say otherwise.
- PyPI publication and additional release channels remain out of scope until explicitly approved.

## Verification

Run from a clean checkout of the exact candidate commit:

```bash
uv sync --locked --all-groups --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not live" -q
uv run thera protocol validate
sh -n install.sh
pwsh -NoProfile -Command '$null = [scriptblock]::Create((Get-Content -Raw install.ps1))'
uv build
uvx twine check dist/*
uv audit --locked
```

Run the configured real-provider gates separately:

```bash
THERA_RUN_CODEX_EVALS=1 \
  uv run pytest tests/test_live_codex_memory.py -m live

THERA_RUN_CODEX_SAFETY_EVALS=1 THERA_CODEX_SAFETY_EVAL_REPEAT=3 \
  uv run pytest tests/test_live_codex_safety.py -m live
```

Run any provider-specific and Telegram smoke tests for configurations claimed in the release. Never
put credentials, real conversations, health information, or other personal data in logs or release
evidence.

Build artifacts once from the candidate commit. Record their SHA-256 checksums and verify the wheel
in a fresh isolated tool environment:

```bash
shasum -a 256 dist/*
uv tool install --force --python 3.12 dist/*.whl
"$(uv tool dir --bin)/thera" protocol validate
"$(uv tool dir --bin)/thera" doctor
```

## Release notes

Human-written notes must include:

1. the public claim and mandatory limitation;
2. the exact intended audience and excluded uses;
3. important changes and migrations;
4. local and external data flows;
5. models/providers and locales exercised by live evaluations;
6. known limitations, residual safety failures, and upstream warnings;
7. supported platforms and revision;
8. artifact checksums;
9. security-report and support links;
10. rollback or withdrawal instructions.

Do not use generated release notes without human claim, privacy, safety, and licensing review.

## Publication and rollback

1. Confirm the candidate commit and all required GitHub checks are green.
2. Create and verify the signed tag.
3. Publish a GitHub prerelease with source archives, built artifacts, checksums, and human notes.
4. Test the documented installation path from the published release, not from a developer checkout.
5. Announce only to the controlled alpha audience and monitor technical, security, privacy, and
   behavioral reports on a best-effort basis.

For a material defect, mark the release as withdrawn, edit the notes with a prominent warning, stop
promoting the affected installation path, and publish a fixed version. Do not delete evidence or
silently replace artifacts. For a vulnerability, follow [SECURITY.md](SECURITY.md) and coordinate
disclosure before publishing sensitive details.
