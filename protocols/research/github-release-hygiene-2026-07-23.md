# GitHub release hygiene review — 2026-07-23

## Scope and method

This review compares commit `279abb3` and the live settings of
[`matteodante/therapist`](https://github.com/matteodante/therapist) with current primary guidance
from GitHub, OpenSSF, SLSA, and PyPA. It is a point-in-time release-readiness review, not a security
certification. No repository setting or implementation was changed.

Priorities mean:

- **P0** — complete before calling the first GitHub prerelease a mature release candidate;
- **P1** — material hardening, or explicitly retain and disclose as an alpha limitation;
- **P2** — useful improvement that does not block the controlled alpha.

## Executive result

The repository has unusually strong community, support, privacy, and release-process documentation
for a single-maintainer alpha. Issue routing, private vulnerability reporting, pinned workflow
dependencies, least-privilege default tokens, dependency updates, secret protection, CodeQL, and
Scorecard are already present.

It is not yet a mature release chain. There is no tag or GitHub release, release immutability is
disabled, release artifacts are not built in a dedicated hosted workflow, and neither build
provenance nor an artifact-specific SBOM is published. `main` also has no protection or ruleset,
while the repository explicitly accepts direct, unreviewed pushes. The current artifact state is
therefore **SLSA Build L0**: tests build artifacts, but no provenance is generated or distributed.
SLSA Build L1 begins when provenance exists; L2 additionally requires signed provenance generated
by a hosted build platform
([SLSA Build Track](https://slsa.dev/spec/v1.2/build-track-basics)).

## Findings and actions

| Area | Current evidence | Assessment | Action |
| --- | --- | --- | --- |
| Issue intake | Four valid issue forms cover bugs, proposals, behavioral/safety failures, and public conduct concerns. `config.yml` disables blank public issues and routes security and support separately. Referenced labels exist. | **Good** | Keep. Test the chooser once from a logged-out/read-only account before release. |
| Security reporting | `SECURITY.md` defines supported scope and synthetic-data rules; GitHub private vulnerability reporting is enabled and linked from the chooser. | **Good; P1 operational gap** | Subscribe the maintainer to security-alert notifications and define a realistic acknowledgment objective. Exercise one private test report, including private-fork and advisory publication steps. |
| Governance and support | `GOVERNANCE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, `PRIVACY.md`, and `RELEASING.md` are present and cross-linked. GitHub reports a 100% community profile. | **Good documentation; P1 continuity gap** | The explicit single-person/no-recovery model cannot satisfy OpenSSF Silver continuity or bus-factor guidance. Add a second recovery-capable maintainer or keep this as a disclosed alpha limitation and do not claim mature multi-person governance. |
| OpenSSF OSPS Baseline | Most public documentation, license, dependency-list, secret-protection, and reporting controls are present. Direct commits to `main` are explicitly allowed, and the account's MFA state was not inspected. | **No OSPS level claim; Level 1 gap** | OSPS Level 1 requires enforcement that prevents direct commits to the primary branch. Verify every control before claiming a level. Level 2 is defined for projects with at least two maintainers, so it is not the current target. |
| Default branch | No branch protection and no repository ruleset; direct pushes to `main` are the documented policy. | **P0 for a “mature RC”; otherwise accepted P1 alpha risk** | Protect `main` against force-push/deletion and require PR-based status checks. A second trusted reviewer is needed before requiring independent approval. If direct pushes remain, do not describe the process as reviewed or mature. |
| Workflow dependencies | Every current `uses:` reference is pinned to a full 40-character commit SHA; Dependabot monitors both `uv` and `github-actions`. | **Good files; P1 enforcement gap** | Enable repository-level “require full-length SHA” and restrict allowed actions to the exact GitHub, Astral, OpenSSF, and CodeQL actions used. Current settings allow all actions and do not enforce SHA pins. |
| Workflow permissions | Repository default `GITHUB_TOKEN` permission is read-only and workflows declare narrow permissions; Actions cannot approve PRs. | **Good** | Preserve job-level permissions. Grant `id-token: write` and `attestations: write` only to the future release-attestation job. |
| Dependency controls | `uv.lock` is committed; Dependabot security updates, alerts, dependency graph, and weekly version updates are enabled; no open Dependabot alerts were observed. | **Good; P1 PR gap** | Add the SHA-pinned dependency review action on `pull_request` and make it required once PRs are the normal path. Decide and document vulnerability and license failure thresholds. |
| CodeQL | GitHub CodeQL default setup scans Python and Actions weekly and on repository events; the current `main` analysis has zero CodeQL results. | **Good** | Keep default setup and inspect the exact candidate SHA before tagging. Do not add a duplicate advanced-setup workflow without a need for custom queries. |
| OpenSSF Scorecard | A scheduled and push-triggered, SHA-pinned Scorecard workflow uploads SARIF. The current scan leaves Branch-Protection, Code-Review, Maintained, Fuzzing, SAST, and Best-Practices findings open. | **Good diagnostic; findings remain** | Resolve branch/review findings or record them as accepted alpha risks. Re-run and triage the SAST finding against the now-active CodeQL evidence. Treat Scorecard as a diagnostic, not certification. |
| Release/tag hygiene | `RELEASING.md` requires SemVer/PEP 440 alignment, a signed annotated tag, prerelease status, checksums, notes, and no tag reuse. No tag or release exists yet. Release immutability is disabled. | **P0** | Enable immutable releases. Create a draft, attach all final assets, then publish it as a prerelease. Never replace an asset or move/reuse a published tag; fix forward with a new version. |
| Build provenance | CI builds and smoke-tests a package, but no dedicated tag/release workflow publishes the exact artifacts, and no artifact attestation exists. | **P0** | Build wheel and sdist once on a GitHub-hosted runner from the exact release tag; attest both outputs with `actions/attest` pinned by SHA; publish the same bytes and document `gh attestation verify`. This moves toward SLSA Build L2 only when the hosted platform signs provenance and consumers verify it. |
| SBOM | GitHub's dependency graph can export a repository-level SPDX SBOM. There is no SBOM describing the released wheel/sdist and no SBOM attestation. | **P0 for mature artifact transparency** | Generate SPDX or CycloneDX for the built distributions, review it for scope and license accuracy, attach it to the draft release, and create an SBOM attestation for the same artifact digests. Do not present the dependency-graph export as an artifact-specific SBOM. |
| Repository metadata | Description, recognized AGPL-3.0 license, README, support/security links, and the maximum 20 lower-case topics are present. The homepage is empty and there is no custom social preview. | **Good; P2 polish** | Keep the precise “adult self-reflection / experimental / not therapy” description. Add a custom social preview if useful. Add a homepage only when a stable project-controlled page exists. |
| Python packaging | `pyproject.toml` uses modern metadata, a recognized SPDX license expression, license files, project URLs, Python requirement, classifiers, and a package version aligned with the planned `v0.1.0`. PyPI is explicitly out of scope. | **Good for GitHub-only alpha** | Continue `uv build` plus `twine check` on the exact candidate. PyPA Trusted Publishing and PEP 740 attestations are not applicable until PyPI publication is approved. |

## Evidence behind the recommendations

### Issue forms and community files

GitHub requires issue forms under `.github/ISSUE_TEMPLATE` with `name`, `description`, and `body`;
the current forms meet that schema. The chooser configuration officially supports
`blank_issues_enabled: false` and `contact_links`, matching the repository
([issue-form syntax](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms);
[template chooser](https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository#configuring-the-template-chooser)).

GitHub's community profile recognizes README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, and
issue/PR templates as the expected public contribution surface. The live repository reports 100%
and additionally provides governance, support, privacy, and release policies
([community profiles](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories)).

OpenSSF Passing requires public contribution, issue, and vulnerability-reporting processes.
OpenSSF Silver additionally requires documented governance, roles, vulnerability response,
dependency monitoring, continuity after loss of one person, and preferably a bus factor of at least
two. Therapist meets much of the documentation surface but explicitly does not meet continuity
([OpenSSF Passing criteria](https://www.bestpractices.dev/en/criteria/0);
[OpenSSF Silver criteria](https://www.bestpractices.dev/en/criteria/1)).

The newer OpenSSF OSPS Baseline 2026.02.19 is a separate control framework. Its Level 1 applies to
projects of any size and requires, among other controls, MFA for sensitive resources, least
privilege for collaborators, secret prevention, public guides, and an enforcement mechanism that
blocks direct commits to the primary branch. Level 2 is scoped to code projects with at least two
maintainers and adds signed release manifests, passing pre-acceptance tests, roles, and a coordinated
vulnerability-disclosure timeframe. Level 3 adds non-author approval, artifact SBOMs, and automatic
SCA/SAST gates. Therapist must not claim any OSPS level from this partial review
([OpenSSF OSPS Baseline 2026.02.19](https://baseline.openssf.org/versions/2026-02-19.html)).

### Vulnerability reporting

GitHub treats `SECURITY.md` and private vulnerability reporting as separate controls. Enabling the
latter provides a secure structured channel; maintainers must also configure notifications to
ensure reports are seen
([security policy](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/add-security-policy);
[private reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)).

The repository has both controls. Its no-guaranteed-deadline wording is honest for one maintainer,
but OpenSSF Passing measures whether actual initial responses are within 14 days. A response target
should be promised only if it can be monitored and met.

### Branch and Actions security

GitHub branch protection can prevent force pushes and deletion and require pull requests, status
checks, signed commits, and resolved conversations. None is enabled here
([protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)).
This matches the documented alpha exception, but not mature change control. SLSA Source L4 likewise
uses required code review as its highest current source-control level
([SLSA Source Track](https://slsa.dev/spec/v1.2/source-requirements)).

GitHub states that a full-length commit SHA is the only immutable way to reference an action and
recommends least-privilege tokens. The workflow files comply, but the live repository setting still
permits all actions and reports `sha_pinning_required: false`; policy enforcement would prevent a
future regression
([secure use of Actions](https://docs.github.com/en/actions/reference/security/secure-use);
[Actions repository settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)).

### Dependency review, CodeQL, and Scorecard

GitHub's dependency review action fails a pull request by default when a package change introduces a
known vulnerability, and it becomes enforceable when the check is required. It complements—not
replaces—Dependabot and lockfile review
([dependency review](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review)).

CodeQL default setup is the appropriate low-maintenance configuration for a public Python
repository and automatically selects languages, query suites, and triggers
([CodeQL default setup](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configure-code-scanning)).
Scorecard's own documentation describes its checks as signals; open findings require triage and are
not proof of a vulnerability or a certification
([OpenSSF Scorecard checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md)).

### Releases, attestations, and SBOM

GitHub immutable releases lock the associated tag and release assets and automatically create a
release attestation. GitHub recommends creating a draft, attaching every asset, and publishing only
when complete
([immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)).
This complements a signed annotated Git tag; it does not replace build provenance for the wheel and
sdist.

GitHub artifact attestations bind an artifact digest to the repository, workflow, commit, and build
identity. The official workflow requires only job-scoped `contents: read`, `id-token: write`, and
`attestations: write`, and the same mechanism supports signed SPDX or CycloneDX SBOM attestations.
GitHub also stresses that attestations provide value only when consumers verify them
([artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations);
[attestation concepts](https://docs.github.com/en/actions/concepts/security/artifact-attestations)).

SLSA provenance records where, when, and how an artifact was produced. Build L1 requires provenance;
Build L2 requires signed provenance from a hosted build platform and consumer verification. No SLSA
level should be claimed until all requirements for the exact released artifacts are checked
([SLSA provenance](https://slsa.dev/spec/v1.2/provenance);
[SLSA verification](https://slsa.dev/spec/v1.2/verifying-artifacts)).

For a future PyPI channel, PyPA recommends Trusted Publishing from GitHub Actions; the official PyPA
publisher produces PEP 740 attestations by default. That advice must not be used to justify a PyPI
workflow now because the project explicitly defers PyPI
([PyPA publishing guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)).

## Minimal mature-RC sequence

1. Resolve the existing legal, provider-policy, privacy, and safety release gates first.
2. Decide whether to replace the documented direct-push exception with protected, PR-based change
   control. If not, label the release a controlled single-maintainer alpha rather than a mature RC.
3. Enforce allowed Actions and full-SHA pinning; add SHA-pinned dependency review.
4. Enable immutable releases.
5. Add one tag-triggered, GitHub-hosted release workflow that builds wheel and sdist once, validates
   them, generates checksums and an artifact-specific SBOM, and attests the artifact digests.
6. Create `v0.1.0` as a signed annotated tag only after version and evidence are final.
7. Create a draft prerelease, attach the exact workflow-built assets, SBOM, checksums, and
   human-reviewed notes, then publish it atomically.
8. Verify the immutable release, tag, checksums, provenance, SBOM attestation, and documented
   installation path as an external consumer would.

Do not claim OpenSSF badge status, SLSA level, independent review, reproducible builds, or a secure
release merely because the corresponding workflow exists. Those are evidence-backed claims that
require their full criteria and verification.
