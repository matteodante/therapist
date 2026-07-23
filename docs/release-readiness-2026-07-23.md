# Public alpha readiness record — 2026-07-23

## Decision

**Technical candidate:** ready for review on `main`  
**Tagged public product release:** no-go  
**Source repository:** public

The code, documentation, packaging, and configured evaluation gates passed on the working candidate.
A tag, GitHub prerelease, installer announcement, or broader promotion remains blocked by the
external legal and provider decisions below. This record is evidence of engineering checks, not
clinical validation, legal approval, or a safety certification.

## Candidate scope

- Name: Therapist.
- Publisher: Matteo Dante, acting as an individual.
- Free, non-commercial, adult-only, single-user self-hosted alpha.
- No PyPI, SaaS, donations, sponsorship, paid support, telemetry, or maintainer-operated inference.
- Claim: “An open-source AI agent for reflection, not code.”
- Mandatory boundary: experimental AI for self-reflection, not therapy, diagnosis, medical advice,
  emergency care, clinical validation, or human monitoring.

## Verified engineering evidence

| Gate | Result |
| --- | --- |
| Ruff lint | Passed |
| Ruff formatting | Passed |
| Offline deterministic suite | 127 passed, 5 live tests deselected |
| Protocol validation | Passed for `therapist.transdiagnostic` |
| Root, nested skill, and reference hash enforcement | Passed |
| POSIX installer syntax | Passed |
| PowerShell installer syntax | Deferred locally because `pwsh` is unavailable; covered by Windows CI |
| Source distribution and wheel build | Passed |
| Twine package metadata check | Passed |
| Locked dependency audit | No known vulnerabilities or adverse project statuses |
| Bilingual live safety evaluation | 10 scenarios × 3 repeats = 30 scenario-runs passed |
| Live longitudinal-memory evaluation | Passed |
| TUI screenshot | Captured from the actual Textual interface with synthetic data |
| GitHub CI, CodeQL, and OpenSSF Scorecard | Passed on the current `main` candidate |

The live safety gate exercised Italian and English cases for possible danger, dependency and
exclusivity, misattunement repair, adverse intervention effects, unsupported diagnosis, and
user-requested understanding before advice, plus the explicit under-18 boundary without durable
state-tool use. The longitudinal gate exercised evidence-linked memory across a simulated extended
interval. Both used the configured experimental personal Codex path; passing does not resolve that
provider's product terms.

## Implemented privacy and supply-chain controls

- ordinary OpenAI Responses calls set and test `store=false`;
- Hugging Face telemetry and implicit credential sending are disabled before client import;
- conversation-time embedding loads use the verified local revision;
- Ollama conversation inference is forced to the loopback endpoint;
- Telegram consent identifies cloud, non-end-to-end-encrypted transport and separate deletion;
- the bot description and setup instructions point to the versioned privacy notice;
- every loaded protocol skill and reference, including the root skill, is hash-verified;
- CI actions are pinned, repository policy enforces full action SHAs and permits only GitHub-owned
  Actions plus the named Astral and OpenSSF actions, CodeQL and GitHub security features are
  enabled, and OpenSSF Scorecard is configured as a diagnostic;
- pull requests receive GitHub dependency review, web commits require a DCO sign-off, releases are
  immutable, and the manual candidate workflow produces checksums, a locked-runtime CycloneDX SBOM,
  and signed provenance and SBOM attestations without publishing a release;
- uv's release manifest, selected archive, and chosen MIT license text are independently verified;
  the license is preserved next to an installer-provided binary;
- the repository has a Code of Conduct, constrained reporting routes, DCO, governance, security,
  privacy, support, contribution, and release documents.

## Accepted single-maintainer limitations

- direct pushes to `main`;
- no mandatory pull request or independent review;
- no second administrator, recovery owner, or promised succession;
- no confidential project-specific conduct inbox;
- best-effort support and security response only.

These limits are public and must not be described as equivalent mature-project controls.

## Open release blockers

1. A qualified EU specialist must record the MDR medical-device qualification for the exact claim,
   functionality, and distribution.
2. GDPR roles, Article 6 and 9 conditions, transfers, provider contracts, and the DPIA decision must
   be approved for the actual release.
3. The publisher/provider role and machine-readable output-marking obligation under EU AI Act
   Article 50 must be decided and implemented where required.
4. Remote provider presets are not release-cleared:
   - Anthropic requires a high-risk mental-health review path not present in Therapist;
   - Gemini requires further paid-service and intended-use review;
   - OpenAI's expected special-category-data coverage is not established;
   - OpenRouter adds an unresolved aggregator and downstream-provider chain;
   - personal Codex OAuth has no documented non-coding subscription contract for this path;
   - arbitrary PydanticAI providers remain unsupported.
5. Telegram still lacks a non-personal confidential privacy contact and requires each bot owner to
   configure the published policy in BotFather.
6. A specific local Ollama reply model and its license and safety behavior must be selected and
   recorded if the first tagged alpha is local-only.

See [compliance-assessment-brief.md](compliance-assessment-brief.md),
[dpia-screening.md](dpia-screening.md), [article-50-assessment.md](article-50-assessment.md), and the
[provider matrix](../protocols/research/provider-data-and-policy-matrix-2026-07-23.md) for the
review packages and primary sources.
