# Open-source release readiness — 2026-07-23

## Status and limits

This is a release-readiness research note, not legal advice or a declaration of compliance. It
summarizes the current repository and primary official sources available on 2026-07-23. The legal
assessment must be repeated if the intended purpose, users, distribution, providers, data flows, or
business model change.

> **Maintainer decision:** the initial external-review gates below were later replaced by the
> proportionate self-assessments in
> [`docs/release-readiness-2026-07-23.md`](../../docs/release-readiness-2026-07-23.md),
> [`docs/dpia-screening.md`](../../docs/dpia-screening.md), and
> [`docs/article-50-assessment.md`](../../docs/article-50-assessment.md) for the narrow free,
> self-hosted alpha. This file preserves the original research recommendations and future
> change-trigger checklist; it is not the current go/no-go record.

The safest first release is a non-commercial, open-source public alpha for adults, positioned
for self-reflection and mental wellbeing rather than therapy or treatment. A hosted service, paid
support, institutional deployment, use with minors, or clinical positioning would materially change
the analysis.

## Executive decision

**Do not announce a public product release yet.** Publishing the source can be appropriate after the
P0 gates in this document are closed, but the repository should not be marketed as a therapist,
clinical tool, medical device, validated mental-health intervention, or replacement for professional
care.

The current implementation already has unusually strong foundations for an early project:

- an AGPL-3.0-or-later license;
- a transparent AI identity and explicit non-clinical limitations;
- encrypted local storage, user export, correction, forgetting, and deletion;
- bounded model context and evidence-linked memory;
- tests for memory integrity, safety behavior, transports, installation, and packaging;
- CI actions pinned to full commit SHAs with least-privilege permissions;
- `README.md`, `CONTRIBUTING.md`, and `SECURITY.md`.

The main release blockers are not code volume. They are the absence of a formally fixed intended
purpose and claim inventory, an operator/data-role decision, a public privacy and data-flow notice,
an Article 50 implementation decision, a documented safety/evaluation release gate, and several
basic community and security-governance files/settings.

## Recommended public positioning

### Primary claim

> **An open-source AI agent for reflection, not code.**

### Supporting line

> Local-first conversations and user-controlled memory for self-reflection and mental wellbeing.

### Mandatory nearby limitation

> Experimental and not clinically validated. It is not therapy, diagnosis, medical advice, or
> emergency care; no human monitors conversations. AI output can be wrong. Your selected model
> provider and, if enabled, Telegram receive the content needed to provide their services.

“Local-first” is more accurate than “local” or “private”: remote model providers and Telegram can
receive highly sensitive content. “For reflection” or “for mental wellbeing” is safer than “for
mental health,” “digital therapist,” “AI therapy,” “therapeutic agent,” or “treatment.”

Do not rely on a bare statement that the software “is not a medical device.” The MDR classification
depends on intended purpose, including functionality, instructions, promotional material, and other
statements. The safer intended-purpose wording is:

> Therapist is intended to support adult self-reflection and organization of user-provided thoughts.
> It is not intended for diagnosis, prevention, monitoring, prediction, prognosis, treatment, or
> alleviation of any disease, disorder, injury, or disability.

That wording is evidence of intent, not a legal conclusion. It must be consistent with the name,
README, package metadata, CLI consent, Telegram bot text, protocol wording, screenshots, examples,
release notes, website, and actual behavior.

## Release model assumed by this assessment

The initial public alpha should explicitly have all of these properties:

- source code and installers are distributed without charge;
- no SaaS, hosted inference, accounts, analytics, advertising, paid support, or commercial data use;
- users operate one private, single-user installation;
- no organization deploys it for patients, clients, employees, students, or other third parties;
- adults only;
- no diagnosis, clinical assessment, treatment plan, medication advice, or emergency monitoring;
- no claims of clinical effectiveness, safety, equivalence to therapy, or regulatory approval;
- the user selects and contracts with any remote model provider and Telegram separately;
- no maintainer receives conversation content unless the user deliberately submits it;
- issue and support channels prohibit personal, health, conversation, credential, and crisis data.

Any departure requires a fresh legal, privacy, medical-device, safety, and security review.

## EU AI Act

### Scope and open-source status

Regulation (EU) 2024/1689 applies to providers placing AI systems on the EU market or putting them
into service, EU deployers, and certain non-EU providers or deployers where output is used in the EU.
An “AI agent” generally qualifies as an AI system.

Article 2(12) excludes some free and open-source systems released outside commercial activity, but
the exclusion does **not** cover systems subject to Article 5 prohibited-practice rules, Article 50
transparency obligations, or high-risk systems. The open-source license therefore does not remove
the obligations most relevant to Therapist.

Recital 103 treats charging, paid support, use through a monetized platform, and personal-data use
beyond security/compatibility/interoperability as possible commercial activity. Merely hosting a
repository is not, by itself, monetization. Document the non-commercial release model and reassess
before accepting commercial sponsorship tied to the product, paid support, hosted operation, or
data-driven monetization.

Primary sources:

- [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Article 2 — scope](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-2)
- [Recital 103 — free and open-source software](https://ai-act-service-desk.ec.europa.eu/en/ai-act/recital-103)
- [European Commission AI-agent FAQ](https://ai-act-service-desk.ec.europa.eu/en/ai-act/faq/how-are-ai-agents-addressed-within-ai-act-0)

### Transparency obligations

Article 50 applies from 2026-08-02. A system directly interacting with a person must disclose that
the person is interacting with AI unless this is already obvious to a reasonably informed,
observant, and circumspect person. The disclosure must be clear, distinguishable, accessible, and
given no later than the first interaction. Therapist should show it before accepting conversation
content in both CLI and Telegram, not only in documentation or `/help`.

Article 50(2) also requires providers of systems generating synthetic text to ensure outputs are
marked in a machine-readable format and detectable as artificially generated or manipulated, subject
to narrow exceptions. Source code is excluded, but conversational replies are generated text.
Before release:

1. map whether Therapist or the selected model provider supplies each required marking;
2. implement and test preservation through CLI, Telegram, copy/export, and plain-text fallbacks where
   technically applicable;
3. document any limitation against the Commission's final Article 50 Guidelines and Code of
   Practice;
4. retain evidence of the decision.

The limited transition period announced for certain pre-existing systems concerns Article 50(2)
marking/detection until 2026-12-02; it should not be treated as a grace period for the direct
interaction disclosure.

Primary sources:

- [Article 50 — transparency obligations](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50)
- [Commission final Article 50 Guidelines](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems)
- [Commission Article 50 questions and answers](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)
- [Recital 132 — interaction disclosure and vulnerable users](https://ai-act-service-desk.ec.europa.eu/en/ai-act/recital-132)

### Manipulation, vulnerability, and relational safety

Article 5 prohibits certain purposefully manipulative or deceptive techniques and exploitation of
vulnerabilities due to age, disability, or social or economic situation when they materially distort
behavior and cause or are reasonably likely to cause significant harm. Psychological harm and harm
accumulating over time are expressly relevant.

For Therapist, this requires more than crisis wording. The product and tests must prevent:

- encouragement of exclusive reliance or withdrawal from human relationships;
- claims that the agent has human feelings, needs the user, or is continuously watching;
- engagement tactics based on vulnerability, fear, guilt, streaks, retention, or remembered distress;
- pressuring the user to continue, disclose, accept an interpretation, or follow an intervention;
- presenting hypotheses as facts or using corrections/forgotten content later;
- escalating emotional intensity to increase usage;
- using minors or other vulnerable groups without a dedicated assessment.

The current relational-safety and evidence-linked-memory architecture is a strong control and should
become an explicit, regression-tested release gate.

Primary sources:

- [Article 5 — prohibited AI practices](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-5)
- [Recital 29 — manipulation and exploitation](https://ai-act-service-desk.ec.europa.eu/en/ai-act/recital-29)
- [Recital 48 — children's rights](https://ai-act-service-desk.ec.europa.eu/en/ai-act/recital-48)

### AI literacy and risk classification

Article 4 has applied since 2025-02-02. A provider or deployer must take measures, to the best of its
ability, to ensure sufficient AI literacy among staff and other persons operating AI systems on its
behalf. Even a small project should maintain a short maintainer document covering model limitations,
privacy boundaries, safety escalation, evaluation interpretation, and secure handling of reports.

Therapist is not automatically high-risk merely because conversations concern wellbeing. It could,
however, become a high-risk system if it is qualified as a medical device whose conformity
assessment requires third-party involvement. This is why the medical-device boundary and claims
cannot be deferred.

Primary sources:

- [Article 4 — AI literacy](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-4)
- [Article 6 — high-risk classification](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6)

### Timing caution

The original regulation generally applies from 2026-08-02, with the original high-risk transition
dates in Article 113. In May 2026 the Council announced a provisional political agreement on the
Digital Omnibus that would move some high-risk dates. As of this note, those amendments are not yet
the consolidated law in EUR-Lex. Do not build a release plan around the proposed delay; monitor the
Official Journal and the consolidated regulation.

Primary sources:

- [Commission AI Act implementation timeline](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)
- [Council AI Act timeline and 2026 provisional agreement](https://www.consilium.europa.eu/en/policies/artificial-intelligence-act/timeline-artificial-intelligence/)

## GDPR and mental-health data

### Role and territorial analysis comes first

Mental-health conversations will commonly reveal “data concerning health,” a GDPR special category.
Encryption and pseudonymization reduce risk but do not make re-identifiable data anonymous.

A natural person operating a private installation for purely personal or household activity may fall
outside the GDPR. That does not automatically exempt the maintainer, Telegram, or a remote model
provider. Controller and processor roles are functional: they depend on who determines each
processing purpose and essential means.

Create a data-role map for every operation:

| Operation | Data recipient | Candidate role requiring confirmation |
| --- | --- | --- |
| Local archive, memory, embeddings | User's device | User/personal-household use; maintainer may have no access |
| Remote inference | Selected model provider | User/controller and provider/processor or independent controller, depending on terms |
| Experimental personal Codex OAuth | OpenAI consumer service | Separate terms; do not assume API enterprise controls or a DPA |
| Telegram transport | Telegram and selected model provider | Independent data flows and terms requiring separate disclosure |
| GitHub issues/security reports | GitHub and maintainers | Maintainer likely determines support/report handling |
| Future telemetry, hosted service, crash reports | Operator and vendors | Operator would normally determine purposes and assume controller duties |

Do not claim “GDPR compliant” until this map, legal bases, Article 9 condition, processor terms,
international transfers, retention, and rights procedures have been reviewed for the actual
operator and distribution model.

Primary sources:

- [GDPR official text](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- [Commission GDPR application guidance](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/application-gdpr_en)
- [EDPB Guidelines 07/2020 on controller and processor concepts](https://www.edpb.europa.eu/documents/guideline/guidelines-072020-on-the-concepts-of-controller-and-processor-in-the-gdpr_en)

### Lawful basis, special-category condition, and consent

Processing requires both an Article 6 legal basis and, when health data is involved, an Article 9
condition. Explicit consent may be a possible Article 9 condition, but it is not a universal answer.
Consent must be freely given, specific, informed, unambiguous, evidenced by a positive act, separable
where appropriate, and as easy to withdraw as to give. National law can add conditions.

The CLI and Telegram consent flows are useful product controls, but their text and behavior must be
reviewed against the chosen role and legal basis. Product use must not be conditioned on optional
processing. Separate the minimum processing required for the selected provider and transport from
any future diagnostics, research, analytics, model training, or feedback.

Primary sources:

- [Commission: sensitive data](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/legal-grounds-processing-data/sensitive-data_en)
- [Commission: conditions for processing sensitive data](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/legal-grounds-processing-data/sensitive-data/under-what-conditions-can-my-companyorganisation-process-sensitive-data_en)
- [Commission: when consent is valid](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/legal-grounds-processing-data/grounds-processing/when-consent-valid_en)
- [EDPB Guidelines 2/2019 on contractual necessity](https://www.edpb.europa.eu/documents/guideline/guidelines-22019-on-the-processing-of-personal-data-under-article-61b-gdpr-in_en)

### Required privacy documentation

Before release, publish a concise privacy and data-flow notice that states:

- who operates the project and how to contact them;
- whether the maintainer receives any conversation content;
- the exact local data categories, locations, encryption boundary, retention, backups, export, and
  deletion behavior;
- each optional external recipient and why data is sent;
- the difference between local models, API providers, personal Codex OAuth, and Telegram;
- provider retention, abuse monitoring, training defaults, subprocessors, regions, and transfer
  mechanism based on verified current terms;
- applicable legal bases and Article 9 condition where the operator is a controller;
- user rights and how to exercise them;
- that deleting local data does not itself delete copies retained by an external provider;
- that no telemetry exists, if that remains true, or a complete account of it if added;
- breach and security-report contact paths;
- the adult-only scope.

OpenAI's API currently states that API data is not used to train models by default unless the
customer opts in, while abuse-monitoring logs are generally retained for up to 30 days. That is not
the same as zero retention, does not describe every product, and must not be generalized to personal
Codex OAuth or other providers.

Primary sources:

- [Commission GDPR obligations](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/obligations_en)
- [Commission data-protection principles](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/principles-gdpr/overview-principles/what-data-can-we-process-and-under-which-conditions_en)
- [Commission international-transfer rules](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/obligations/what-rules-apply-if-my-organisation-transfers-data-outside-eu_en)
- [OpenAI API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)

### DPIA screening and minors

Run and retain a Data Protection Impact Assessment screening before release. A single-user local
installation is not automatically “large scale,” but this product combines innovative AI,
longitudinal profiling, inferred patterns, sensitive mental-health content, and potentially vulnerable
people. The Italian supervisory authority's DPIA list treats combinations of evaluation/profiling,
sensitive data, vulnerable users, and innovative technology as high-risk indicators. A hosted or
institutional version would make a full DPIA much more likely.

Keep the public alpha adult-only unless a dedicated child-rights, safeguarding, age-assurance,
consent, clinical, privacy, and design assessment is completed. GDPR Article 8 sets special rules
where consent is the basis for information-society services offered directly to children; the
default threshold is 16, and Member States can lower it to no less than 13. Adult-only scope is a
risk boundary, not a substitute for proportionate implementation.

Primary sources:

- [Commission: when a DPIA is required](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/obligations/when-data-protection-impact-assessment-dpia-required_en)
- [Italian Garante DPIA list](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9058979)
- [GDPR Article 8 in the official regulation](https://eur-lex.europa.eu/eli/reg/2016/679/oj)

## EU Medical Device Regulation boundary

### Why the boundary is material

Under Regulation (EU) 2017/745, software can be a medical device when the manufacturer intends it
for diagnosis, prevention, monitoring, prediction, prognosis, treatment, or alleviation of disease,
injury, or disability. Intended purpose is determined from labels, instructions, promotional and
sales material, statements, and clinical evaluation, not from one disclaimer.

General-purpose and lifestyle/wellbeing software is not medical-device software merely because it
concerns wellbeing. The boundary becomes difficult when a product uses personalized “therapeutic”
interventions, monitors symptoms, or claims to alleviate a disorder.

MDCG 2019-11 rev.1 gives directly relevant medical-device examples:

- software intended to alleviate eating-disorder behaviors through personalized psychoeducational
  workshops;
- software aiding schizophrenia treatment through symptom monitoring and personalized
  interventions.

Therapist's name, “therapeutic techniques,” longitudinal “case formulation,” personalized
interventions, outcome tracking, and mental-health positioning create a non-trivial classification
risk even though the current documentation rejects diagnosis and clinical claims.

Primary sources:

- [Regulation (EU) 2017/745](https://eur-lex.europa.eu/eli/reg/2017/745/oj)
- [MDCG 2019-11 rev.1 — qualification and classification of software](https://health.ec.europa.eu/document/download/b45335c5-1679-4c71-a91c-fc7a4d37f12b_en?filename=mdcg_2019_11_en.pdf)
- [Commission publication page for MDCG 2019-11 rev.1](https://health.ec.europa.eu/latest-updates/update-mdcg-2019-11-rev1-qualification-and-classification-software-regulation-eu-2017745-and-2025-06-17_en)
- [MDCG 2025-6 — interplay between medical-device law and the AI Act](https://health.ec.europa.eu/latest-updates/mdcg-2025-6-faq-interplay-between-medical-devices-regulation-vitro-diagnostic-medical-devices-2025-06-19_en)

### P0 medical-device gate

Before public marketing:

1. approve one intended-purpose statement;
2. inventory every claim and product term across all public and runtime surfaces;
3. remove or qualify language that implies diagnosis, treatment, symptom monitoring, clinical
   decision support, efficacy, recovery, or equivalence to a professional;
4. verify that behavior and examples are consistent with the claim;
5. obtain a written EU medical-device classification assessment from qualified counsel or a
   regulatory specialist;
6. record a change trigger requiring reassessment if the product adds symptom scales, clinical
   pathways, clinician dashboards, medical recommendations, institutional deployment, or efficacy
   claims.

If the intended purpose falls inside the MDR, do not release it as a medical product until the
applicable quality, clinical evaluation, risk management, conformity assessment, registration,
post-market, and AI Act requirements are implemented. Open source is not an exemption from those
product rules.

## Safety, evidence, and provider policy

### What official health guidance supports

WHO guidance supports autonomy, wellbeing, safety, transparency, accountability, inclusiveness,
privacy, lifecycle documentation, defined intended use, validation, cybersecurity, and post-release
monitoring. It also warns that health-oriented generative models can produce false, inaccurate,
biased, or incomplete output and can create automation bias.

The NICE Evidence Standards Framework can help design a future evidence plan for a digital health
technology in the NHS. It is not an approval, does not itself establish product safety, and must not
be cited as evidence that Therapist is clinically effective or “NICE compliant.”

These sources support a cautious engineering process. They do not validate autonomous AI therapy.

Primary sources:

- [WHO ethics and governance of AI for health](https://www.who.int/publications/i/item/9789240029200)
- [WHO's six AI-for-health principles](https://www.who.int/news/item/28-06-2021-who-issues-first-global-report-on-ai-in-health-and-six-guiding-principles-for-its-design-and-use)
- [WHO guidance on large multimodal models for health](https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models)
- [WHO regulatory considerations for AI in health](https://www.who.int/publications/i/item/9789240078871)
- [NICE Evidence Standards Framework](https://www.nice.org.uk/corporate/ecd7)
- [NICE evidence-standard tables](https://www.nice.org.uk/corporate/ecd7/chapter/section-c-evidence-standards-tables)
- [NICE ESF user guide](https://www.nice.org.uk/Media/Default/About/what-we-do/our-programmes/evidence-standards-framework/evidence-standards-framework-for-digital-health-technologies-user-guide.pdf)

### Provider-policy gate

OpenAI's current Usage Policies prohibit tailored advice that requires a license, such as medical
advice, without appropriate involvement by a licensed professional, and restrict high-stakes medical
decisions without human review. They also prohibit promotion or facilitation of suicide, self-harm,
and disordered eating.

Because Therapist has no licensed clinician in the loop, the OpenAI-backed modes must remain within
self-reflection and general wellbeing, not individualized medical advice or clinical decisions.
Provider terms and safety policies can change; review all supported providers before every release
and keep provider-specific tests or disable an incompatible adapter.

Primary sources:

- [OpenAI Usage Policies](https://openai.com/policies/usage-policies/)
- [OpenAI on sycophancy and emotional over-reliance](https://openai.com/index/expanding-on-sycophancy/)

### Minimum safety release suite

The release gate should record the model, provider revision, protocol commit, locale, and result for
multi-turn Italian and English scenarios covering:

- transparent AI identity and no implied human monitoring;
- no diagnosis, medication recommendation, treatment claim, or professional impersonation;
- possible danger and emergency-resource routing without claiming emergency monitoring;
- dependency, exclusivity, guilt, coercion, and withdrawal from human support;
- misattunement and user rejection of an intervention;
- adverse effects that stop the intervention before another technique;
- hallucinated memories and unsupported personal claims;
- exact provenance, tentative hypotheses, confirmation, correction, forgetting, and deletion;
- old-session retrieval and absence of corrected/forgotten content;
- malicious prompt content attempting to override safety or expose private instructions;
- provider refusal, timeout, partial output, invalid tool calls, and interrupted consolidation;
- remote-provider and Telegram consent before sensitive content is sent;
- context limits, archive boundaries, and no secrets or health content in logs;
- model variability across repeated runs and documented residual failures.

Passing tests demonstrate defined behavior under tested conditions. They are not clinical validation
or proof of safety.

## Open-source repository maturity

### Proportionate target

Use the [OpenSSF OSPS Baseline v2026.02.19](https://baseline.openssf.org/versions/2026-02-19)
Level 1 as the initial publication gate. Level 2 assumes at least two maintainers; Level 3 assumes a
broad user base and is premature. Also register the project as “in progress” for the
[OpenSSF Best Practices Badge](https://www.bestpractices.dev/en/criteria/0) and target a passing
badge before calling the project stable.

Run [OpenSSF Scorecard](https://www.scorecard.dev/) as a diagnostic, not a certification. Its
heuristics should inform work, not replace review.

### P0 — required before the public announcement

| Area | Required action |
| --- | --- |
| Claims | Approve the claim, intended-purpose statement, claim inventory, and prohibited-claims list |
| Legal | Record operator/owner, adult-only/non-commercial scope, jurisdictions, and counsel's MDR assessment |
| Privacy | Publish the data-flow/privacy notice, controller/processor map, provider matrix, transfer review, and DPIA screening |
| AI Act | Disclose AI before first input; close and document the Article 50(2) marking decision; document AI literacy |
| Safety | Publish limitations and crisis boundary; run the bilingual safety release suite and record residual risks |
| Sensitive reports | Issue/support forms must say never to submit conversation, health, crisis, token, key, or other personal data |
| Conduct | Add an enforceable `CODE_OF_CONDUCT.md` with a monitored private enforcement contact |
| Support | Add `SUPPORT.md` defining community support, response limits, no crisis/clinical support, and safe report channels |
| Governance | Add a minimal `GOVERNANCE.md`: maintainer, decision rights, release authority, conflict handling, and succession |
| Contribution | Extend contribution guidance with test, documentation, security, privacy, safety, and DCO/CLA policy |
| Templates | Add bug, feature, safety/privacy, and documentation issue forms plus a pull-request template |
| Security | Enable and verify private vulnerability reporting, Dependabot alerts, secret scanning/push protection where available, and CodeQL |
| Branch protection | Protect `main`: pull requests, required CI, resolved conversations, no force push or deletion; do not require a nonexistent second reviewer |
| Dependencies | Configure automated updates for GitHub Actions and the supported Python/`uv` dependency files |
| Releases | Define alpha versioning, supported versions, signed/tagged release ownership, human release notes, rollback, and disclosure process |

Relevant official sources:

- [GitHub community-profile files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories)
- [GitHub default community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [GitHub Code of Conduct guidance](https://docs.github.com/en/free-pro-team%40latest/communities/setting-up-your-project-for-healthy-contributions/adding-a-code-of-conduct-to-your-project)
- [GitHub issue forms and templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository)
- [GitHub pull-request templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository)
- [GitHub repository rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
- [GitHub secure use of Actions](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Dependabot version updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-version-updates)

### P1 — before a stable release or broad installer promotion

- publish checksums and a software bill of materials for release artifacts;
- generate build provenance/artifact attestations;
- add OpenSSF Scorecard on a scheduled and default-branch run, upload SARIF, and pin the action by
  full SHA;
- obtain the OpenSSF Best Practices passing badge;
- establish a human security-response target and supported-version table;
- document deterministic build inputs and perform clean-environment install/upgrade/uninstall tests;
- require DCO sign-off if the project wants explicit per-commit contributor authorization;
- move release credentials out of long-lived secrets; if PyPI publishing is enabled later, use PyPI
  Trusted Publishing and attestations;
- document third-party notices, protocol-source licensing, and generated/bundled asset provenance;
- publish a model/provider compatibility and safety matrix.

Primary sources:

- [GitHub SBOM export](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/export-dependencies-as-sbom)
- [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- [Developer Certificate of Origin](https://developercertificate.org/)
- [GitHub commit sign-off policy](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-the-commit-signoff-policy-for-your-repository)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [PyPI digital attestations](https://docs.pypi.org/attestations/)

### P2 — when the project has multiple maintainers or material adoption

- move the repository to an organization with at least two secured administrators;
- add `CODEOWNERS` and require independent review for sensitive areas;
- adopt OpenSSF OSPS Level 2 controls;
- document maintainer nomination/removal and conflict-of-interest rules;
- run an independent security assessment and threat model;
- create a structured incident, safety-event, and coordinated-disclosure process;
- commission clinical/human-factors research before making any efficacy claim;
- reassess product liability, consumer law, MDR, AI Act, GDPR, CRA, and insurance for each
  distribution model.

Formal foundation-style governance, a CLA, complex working groups, multiple release trains, and
enterprise infrastructure are not justified for a single-maintainer alpha. GitHub and the Open
Source Guides note that most projects do not require a CLA; a clear inbound=outbound contribution
rule plus optional DCO is proportionate.

Primary sources:

- [Open Source Guides: leadership and governance](https://opensource.guide/leadership-and-governance/)
- [Open Source Guides: legal considerations](https://opensource.guide/legal/)

## Cyber Resilience Act watch item

Regulation (EU) 2024/2847 is adjacent to, and separate from, the AI Act. Free and open-source software
supplied outside commercial activity is generally outside manufacturer obligations, but monetization,
paid support, platform operation, or qualifying stewardship can change the result. Full application
is scheduled for 2027-12-11; vulnerability-reporting obligations start earlier, on 2026-09-11.

Document why the first release is outside commercial activity and reassess before changing that
model. Irrespective of scope, use the CRA's vulnerability-handling principles as good practice.

Primary sources:

- [Regulation (EU) 2024/2847](https://eur-lex.europa.eu/eli/reg/2024/2847/oj)
- [Commission Cyber Resilience Act summary](https://digital-strategy.ec.europa.eu/en/policies/cra-summary)

## Final release checklist

The maintainer should be able to answer **yes**, with a linked artifact or test report, to every item
before the public announcement:

- [ ] A single intended purpose and public claim are approved and consistent everywhere.
- [ ] Qualified EU counsel has documented the medical-device classification assessment.
- [ ] The initial operator, users, age boundary, jurisdictions, and non-commercial model are fixed.
- [ ] The privacy/data-flow notice and provider matrix match actual code and current provider terms.
- [ ] GDPR roles, legal bases, Article 9 condition, transfers, retention, rights, and DPIA screening
      are documented where applicable.
- [ ] AI identity is disclosed before first input in every transport.
- [ ] The Article 50 machine-readable marking decision is implemented, tested, and documented.
- [ ] No user-facing text promises privacy, confidentiality, compliance, safety, clinical benefit,
      or crisis monitoring beyond what is demonstrably true.
- [ ] Adult-only scope and no-clinical-use boundary are explicit.
- [ ] The bilingual safety release suite passes and residual risks are published.
- [ ] Community and support channels prohibit sensitive or crisis content.
- [ ] Code of Conduct, support, governance, issue forms, PR template, and contribution rules exist.
- [ ] Private vulnerability reporting and repository security features are enabled and verified.
- [ ] `main` is protected and required CI is green.
- [ ] Dependency updates, static/security analysis, installer tests, packaging tests, and secret
      scanning are active.
- [ ] Alpha version, signed/tagged release, release notes, checksums, rollback, and supported-version
      policy are defined.
- [ ] The AGPL license, third-party notices, protocol sources, bundled-model licensing, and generated
      artifacts have been reviewed.
- [ ] Documentation states that the alpha is experimental and not clinically validated.
- [ ] A named maintainer has final release authority and a second person can recover project access.

## Questions that change the legal assessment

Resolve these before implementation work is considered release-complete:

1. Who is the legal publisher/operator: an individual, company, association, or future foundation?
2. Is the first release strictly adults-only, and how will that boundary be communicated and
   enforced proportionately?
3. Will there be donations, sponsorship, paid support, a hosted service, an app store, or any
   maintainer-controlled inference?
4. Which model providers, products, regions, retention modes, and contractual terms are supported?
5. May an independent third-party client use personal Codex OAuth and the direct backend as this
   conversation provider under current OpenAI terms and policy?
6. Will any maintainer ever receive conversations, exports, logs, crash reports, or evaluation data?
7. Are interventions intended only as general reflection prompts, or to alleviate named symptoms or
   conditions?
8. Which countries will be actively marketed to, rather than merely allowing source access?
9. What evidence threshold would be required before changing “experimental” or making any benefit
   claim?
10. Who handles private security, privacy, safety, and conduct reports, and what response capacity
    actually exists?

These answers should become versioned release assumptions. A changed answer is a mandatory review
trigger, not merely a documentation update.
