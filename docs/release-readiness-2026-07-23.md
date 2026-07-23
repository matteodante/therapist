# Public alpha readiness record — 2026-07-23

## Decision

**Technical candidate:** ready for review on `main`  
**Tagged public product release:** ready after the remaining operational release checks
**Source repository:** public

The code, documentation, packaging, and configured evaluation gates passed on the working candidate.
A tag and GitHub prerelease still require the release mechanics and live Telegram smoke test listed
below. The proportionate EU and privacy self-assessments for this narrow release are recorded; an
external legal opinion is not a gate for the current free self-hosted alpha. This record is evidence
of engineering checks, not clinical validation, legal approval, or a safety certification.

## Candidate scope

- Name: Therapist.
- Publisher: Matteo Dante, acting as an individual.
- Free, non-commercial, adult-only, single-user self-hosted alpha.
- No PyPI, SaaS, donations, sponsorship, paid support, telemetry, or maintainer-operated inference.
- Supported release configuration: CLI and private Telegram using a personal ChatGPT Plus/Pro
  account through the experimental `codex:` OAuth provider.
- Other local and PydanticAI conversation providers are technical escape hatches and are not
  advertised or release-cleared for this alpha.
- Claim: “An open-source AI agent for reflection, not code.”
- Mandatory boundary: experimental AI for self-reflection, not therapy, diagnosis, medical advice,
  emergency care, clinical validation, or human monitoring.

## Verified engineering evidence

| Gate | Result |
| --- | --- |
| Ruff lint | Passed |
| Ruff formatting | Passed |
| ty static type check | Passed for `src/therapist` |
| Branch coverage | 75% minimum enforced |
| Offline deterministic suite | 131 passed, 5 live tests deselected |
| Protocol validation | Passed for `therapist.transdiagnostic` |
| Root, nested skill, and reference hash enforcement | Passed |
| POSIX installer syntax | Passed |
| PowerShell installer syntax | Deferred locally because `pwsh` is unavailable; covered by Windows CI |
| Source distribution and wheel build | Passed |
| Twine package metadata check | Passed |
| Locked dependency audit | No known vulnerabilities or adverse project statuses |
| Bilingual live safety evaluation | 10 scenarios × 3 repeats = 30 scenario-runs passed |
| Live longitudinal-memory evaluation | Passed |
| Private Telegram live smoke test | Passed on the allowlisted bot: privacy and status views, persistent text delivery, text-only media rejection, and no durable memory from an explicitly synthetic message |
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
- `main` rejects force pushes and deletion while preserving the documented direct-push workflow;
- uv's release manifest, selected archive, and chosen MIT license text are independently verified;
  the license is preserved next to an installer-provided binary;
- the repository has a Code of Conduct, constrained reporting routes, DCO, governance, security,
  privacy, support, contribution, and release documents.

## Accepted single-maintainer limitations

- direct pushes to `main`;
- no mandatory pull request or independent review;
- no second administrator, recovery owner, or promised succession;
- no confidential project-specific conduct inbox;
- experimental personal ChatGPT Codex OAuth may change or stop working, is not the OpenAI API, and
  carries no compatibility, availability, or endorsement claim;
- best-effort support and security response only.

These limits are public and must not be described as equivalent mature-project controls.

## Publication authorization

The maintainer approves package version `0.1.0`, signed tag `v0.1.0`, and a GitHub prerelease from
the exact final `main` candidate once its required checks and candidate workflow pass. The supported
installer channel is the release-tagged `install.sh` and `install.ps1`; both install the immutable
`v0.1.0` source rather than a moving branch.

The current privacy screening does not identify publisher-side application-data processing: there is
no hosted instance, central account, telemetry, maintainer inference, or normal access to user data.
The published notice, consent surfaces, local data controls, `/privacy`, and per-operator BotFather
policy configuration are the proportionate controls for this release. A dedicated privacy mailbox,
external GDPR opinion, and full DPIA are not current release gates.

The intended purpose expressly excludes the medical purposes that would qualify software under the
MDR. Article 50 interaction disclosure is already implemented. Medical-device, data-protection, and
AI Act assessments remain change-triggered legal risks rather than claims of compliance: re-open
them before SaaS, telemetry, maintainer access, organizational or clinical use, minors, efficacy or
treatment claims, or any legally required output-marking deadline.

See [compliance-assessment-brief.md](compliance-assessment-brief.md),
[dpia-screening.md](dpia-screening.md), [article-50-assessment.md](article-50-assessment.md), and the
[privacy and regulatory proportionality assessment](../protocols/research/privacy-and-regulatory-proportionality-2026-07-23.md)
and [provider matrix](../protocols/research/provider-data-and-policy-matrix-2026-07-23.md) for the
review records and primary sources.
