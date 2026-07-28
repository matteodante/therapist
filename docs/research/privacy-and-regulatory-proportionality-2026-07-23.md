# Privacy and EU regulatory proportionality — 2026-07-23

## Purpose, limits, and fixed assumptions

This note is a point-in-time release assessment based only on official Telegram, EU, EDPB, and
European Commission sources. It is not legal advice, a compliance certificate, or a substitute for
advice on facts that differ from those below.

The assessment assumes the first Therapist alpha is:

- free, non-commercial, open-source software published by one individual;
- installed and operated by one adult for private self-reflection;
- self-hosted, with no publisher-operated service, account, telemetry, advertising, analytics,
  payment, central inference, or publisher access to conversation content;
- limited to a local CLI and one private, allowlisted Telegram bot owned and configured by the
  operator;
- dependent on an operator-supplied personal remote-model account for conversation inference;
- expressly not intended to diagnose, prevent, monitor, predict, prognose, treat, or alleviate a
  disease, disorder, injury, or disability.

The result changes if the publisher operates infrastructure, receives user content, introduces
telemetry or payments, targets organisations or clinicians, supports multiple people, admits
minors, or makes medical-purpose or efficacy claims.

## Executive conclusion

The official sources do **not** support treating a dedicated privacy email address, commissioned
legal opinion, formal publisher-side DPIA, or prior regulatory approval as a mandatory gate for
publishing this exact alpha.

The proportionate release position is:

1. **Telegram has concrete operator obligations.** Each person who creates and operates a bot must
   expose an accurate privacy policy, configure that policy through BotFather when Telegram's
   standard policy does not match, delete data when required, minimise collection, protect
   credentials, and encrypt stored Telegram-derived user data separately from its key.
2. **Publishing source code does not itself give the publisher access to, or constitute
   publisher-side processing of, conversation data.** GDPR roles remain functional and must be
   assessed against actual processing. A private operator may fall within the personal/household
   exemption; remote service providers remain responsible for their own processing.
3. **If GDPR applies to an operator, one Article 6 basis and, when the content reveals health or
   other special-category data, one Article 9 condition are required.** A full DPIA is required
   where the actual processing is likely to create high risk. The Commission distinguishes limited
   from large-scale sensitive-data processing, while Italy's official Article 35(4) list also
   requires a DPIA when innovative technology such as AI occurs with another EDPB risk criterion.
4. **The current non-medical intended purpose supports a reasonable outside-MDR self-assessment.**
   Current MDCG guidance says software must have its own medical purpose to qualify as medical
   device software and expressly lists wellness apps as non-MDSW. All product claims and actual
   functions must remain consistent with that purpose.
5. **AI Act Article 50 is an imminent operational deadline, not a reason to block a prerelease on
   23 July 2026.** It applies from 2 August 2026. Explicit AI identity from the first interaction is
   the clear minimum. Machine-readable marking is a separate provider obligation that requires a
   documented scope decision; the Commission describes a limited transition until 2 December 2026
   for Article 50(2) systems placed on the market before 2 August 2026.

None of these conclusions supports a general “GDPR compliant”, “MDR exempt”, “AI Act compliant”,
clinically safe, or regulator-approved claim.

## Decision matrix

| Topic | Effective requirement for this alpha | Conditional requirement | Conservative extra, not established as a release prerequisite |
| --- | --- | --- | --- |
| Telegram privacy policy | Each bot must have an easily accessible, accurate policy. Configure a custom policy in BotFather when Telegram's standard policy does not fit. | The operator's notice must also satisfy applicable local law. | A separate publisher privacy mailbox where the publisher receives no conversation data. |
| Telegram deletion and security | Delete Telegram-derived user data without undue delay when requested or no longer needed; encrypt it at rest separately from the key; secure bot credentials. | Notify affected users of a breach as applicable by law. | External privacy audit before the first single-user alpha. |
| GDPR role | Determine roles from who actually decides the purposes and essential means of each processing operation. | The operator may be outside GDPR for purely personal/household activity; providers processing the data are not exempt merely because the user's activity is private. | Declaring the source-code publisher controller or processor for every independent installation without analysing actual access and decisions. |
| GDPR Articles 6 and 9 | No publisher-side basis is needed for conversation data the publisher does not process. | An in-scope operator must document an Article 6 basis and, for special-category data, an Article 9 condition such as valid explicit consent when appropriate. | Treating a consent banner alone as proof of compliance for every provider, transfer, or organisational use. |
| DPIA | Perform and record a screening against the real processing. | A DPIA is mandatory when processing is likely to result in high risk, including the listed large-scale or systematic cases and any applicable national authority list. In-scope Italian operation using AI on special-category or highly personal data can satisfy the Italian listed combination. | A full commissioned DPIA for distributing zero-telemetry source code, irrespective of actual processing. |
| MDR | Keep the intended purpose and every public claim clearly non-medical. | Reassess before adding disease, symptom, diagnosis, monitoring, prognosis, treatment, alleviation, clinical decision-support, or efficacy claims/functions. | An external MDR opinion as an automatic prerequisite despite a stable non-medical wellness purpose. |
| AI Act Article 50(1) | Ensure a clear, distinguishable AI disclosure no later than the first interaction; do not rely only on the product name or on “obviousness”. | Applies from 2 August 2026 to providers of systems directly interacting with natural persons. | Blocking a 23 July 2026 prerelease even though the disclosure is already a low-cost control and the obligation is not yet applicable. |
| AI Act Article 50(2) | Record a provider/scope and marking decision before the applicable deadline. | Providers of systems generating synthetic text may need effective machine-readable output marking. The open-source exception does not remove Article 50. | Assuming either that a plain-text CLI is automatically exempt or that it must implement an unverified technical format immediately. |

## Telegram Bot Platform

### What Telegram actually requires

Telegram's [Bot Platform Developer Terms](https://telegram.org/tos/bot-developers) require every bot
or third-party app to be bound by an easily accessible privacy policy that explains what data is
stored, how it is collected, and why. Telegram supplies a standard policy by default, but if that
policy does not accurately describe the bot, the developer must provide a custom policy through
BotFather.

For Therapist, Telegram's generic standard policy is not enough because the bot sends voluntarily
provided conversation text to a remote model provider and stores an encrypted local archive.
Accordingly, each operator should:

- configure the repository's current `PRIVACY.md` URL through BotFather;
- keep `/privacy` available inside the bot;
- show the Telegram-specific consent and data-flow notice before accepting conversation input.

Telegram's official [`botInfo` schema](https://core.telegram.org/constructor/botInfo) confirms that
the client opens the configured `privacy_policy_url`; if none is set, it uses `/privacy` when that
command is supported, otherwise it opens Telegram's standard bot policy. This is evidence that a
policy URL and `/privacy` are valid accessibility mechanisms, not that one operator can configure
other users' independently owned bots.

The same Developer Terms require, without undue delay and subject to applicable law, deletion on a
user or Telegram request, when data is no longer needed, when the bot ceases operating, and on a
lawful authority request. They also require:

- collecting only data essential to the service;
- clear information plus individual, explicit, active, revocable consent for data voluntarily
  submitted to the bot;
- encryption at rest with the encryption key stored separately;
- a reasonably secure operating environment, remediation of leaks, and protection of credentials.

Therapist's encrypted local SQLite store, separate local key, allowlisted single user, local
export/deletion commands, and pre-chat consent are directly aligned with these platform controls.
The operator still controls Telegram's cloud copy: local deletion cannot erase the Telegram chat,
so the product must continue to say this plainly.

Telegram's [Privacy Policy, sections 3.3 and 6](https://telegram.org/privacy) states that ordinary
bot chats are cloud chats and that bot developers receive messages sent to their bot plus public
account data. This supports the existing disclosure that Telegram receives and retains the
transport copy and that bot chats are not end-to-end encrypted.

### Contact-channel conclusion

The reviewed Telegram terms require an accessible privacy policy, but do not prescribe a dedicated
email address or confidential publisher inbox.

Where GDPR applies to an operator, Articles 13 and 14 require the controller's identity and contact
details. The [GDPR text](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679) and
the Commission's [notice checklist](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/principles-gdpr/what-information-must-be-given-individuals-whose-data-collected_en)
require contact details, but do not specify that they must be an email address. The channel must be
genuine and usable for the rights it claims to support.

For the current product, each operator is the only person who can answer requests about their local
installation. Requiring the upstream source-code publisher to operate a private inbox for
conversations the publisher cannot access is therefore a conservative governance preference, not a
requirement established by these sources.

## GDPR

### Roles follow actual processing

Under the Commission's
[controller/processor explanation](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/obligations/controllerprocessor/what-data-controller-or-data-processor_en)
and the EDPB's final
[Guidelines 07/2020](https://www.edpb.europa.eu/documents/guideline/guidelines-072020-on-the-concepts-of-controller-and-processor-in-the-gdpr_en),
a controller decides the purposes and essential means—the “why” and “how”—of processing.
Controller and processor are functional roles based on facts, not labels in documentation.

Applying that rule to the fixed assumptions:

- publishing and maintaining code, without receiving conversation content or operating the
  installation, is not itself processing those conversations;
- the person operating the installation chooses to start the conversation, owns the local archive,
  selects the providers, and controls deletion;
- Telegram and the remote model provider process the data they receive under roles that must be
  assessed from their actual services and terms;
- an upstream publisher could acquire a role later by adding telemetry, support access, hosted
  inference, central accounts, or another processing purpose.

This is a fact-based inference from the official role test, not a binding authority decision about
Therapist.

### Household use and external providers

The Commission's
[GDPR application guidance](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/application-gdpr_en)
states that GDPR does not apply to processing by an individual for purely personal or household
reasons without professional or commercial connection. Article 2(2)(c) and Recital 18 preserve the
obligations of controllers or processors that provide processing means even when the natural
person's own activity is exempt.

Therefore, a one-adult private installation may fall within the household exemption, but that does
not make Telegram or a cloud-model provider unregulated, erase their data flows, or extend to a
professional, clinical, employer, public, shared, or commercial deployment.

### Articles 6 and 9

The Commission's
[legal-ground summary](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/legal-grounds-processing-data_en)
lists the six Article 6 bases and the additional Article 9 conditions for special categories.
Health-related data and data about sex life or sexual orientation are protected special categories.
Therapist conversation text can contain them even though the product has no medical intended
purpose.

If an operator's processing is in scope, the operator must identify:

1. a valid Article 6 basis for each purpose; and
2. when Article 9 data is processed, a valid Article 9 exception.

Explicit consent under Article 9(2)(a) may be available for a voluntary private service, but it must
be specific, informed, freely given, affirmative, and withdrawable. It is not a universal substitute for
provider-role, transfer, retention, security, or processor-contract analysis. A future
professional, employer, clinical, or multi-user version must perform a fresh assessment rather than
inherit this alpha conclusion.

### DPIA threshold

Article 35 requires a DPIA where processing is likely to result in a high risk to people's rights
and freedoms. The Commission's
[DPIA guidance](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/obligations/when-data-protection-impact-assessment-dpia-required_en)
identifies at least:

- systematic and extensive evaluation of personal aspects based on automated processing;
- large-scale processing of sensitive data;
- systematic monitoring of public areas on a large scale.

It also gives limited sensitive-data processing by a community doctor as an example where a DPIA is
not required because it is not large-scale. National supervisory authorities may publish additional
mandatory lists, and residual unmitigated high risk requires prior consultation with the authority.

For an operator subject to Italian GDPR enforcement, the Garante's official
[11 October 2018 Article 35(4) list](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9058979)
adds an important condition. Item 7 requires a DPIA for processing through innovative technologies,
expressly including AI and online voice assistants with text scanning, whenever at least one other
EDPB high-risk criterion is also present. Those criteria include sensitive or highly personal data.
Accordingly, a non-household Italian operator using Therapist on identifiable mental-health
conversation content should not rely on “single user” alone: the AI-plus-sensitive-data combination
can require a proportionate DPIA even without large scale.

A repository-side screening remains sensible because conversations are sensitive and the agent
builds longitudinal patterns. On the fixed facts, however, the publisher does not operate the
processing, the installation is a natural person's private non-professional activity, there is no
public monitoring, and there is no large-scale dataset. The sources therefore support recording a
**screened, conditional DPIA position**, not making a commissioned full DPIA or prior DPA
consultation an automatic source-code release gate. An operator who is not within the household
exemption must run the Italian item-7 test before processing.

Re-screen on any change to scale, users, operator access, automated decisions with significant
effects, clinical context, minors, telemetry, or central processing.

## EU Medical Device Regulation

The Commission's current
[MDCG 2019-11 rev.1 software guidance](https://health.ec.europa.eu/document/download/b45335c5-1679-4c71-a91c-fc7a4d37f12b_en?filename=mdcg_2019_11_en.pdf)
states that software must have a medical purpose of its own to qualify as medical device software.
The intended purpose is derived from the manufacturer's labels, instructions, promotional or sales
materials, statements, and clinical evaluation—not from one disclaimer in isolation.

The same guidance says:

- software with only non-medical purposes, including wellness or fitness apps, does not qualify as
  MDSW;
- software intended to diagnose, prevent, monitor, predict, prognose, treat, or alleviate disease
  can qualify;
- personalised software intended to alleviate eating-disorder symptoms or aid schizophrenia
  treatment is given as MDSW;
- the risk of harm by itself is not the qualification criterion; intended medical purpose is.

Therapist's present purpose—adult self-reflection and organisation of user-provided thoughts,
without diagnosis, disease monitoring, treatment, symptom alleviation, prescriptions, medical
advice, or clinical claims—supports a reasonable current self-assessment that it is a non-medical
wellness product outside MDSW.

That conclusion depends on consistency. Public metadata should prefer “an experimental AI agent for
adult self-reflection” over the unqualified claim “an agent for mental health.” Conversation
behavior must not quietly introduce disease-specific treatment, symptom monitoring, clinical
recommendations, or efficacy promises that contradict the stated purpose. Re-screen before any such
change.

The reviewed MDR and MDCG sources do not require a manufacturer to commission external counsel
before deciding that plainly non-medical wellness software is outside MDSW. External review is
useful for a borderline or expanded product, but it is a risk-management choice rather than an
identified prerequisite for this alpha.

## EU AI Act Article 50

### Scope and dates

[Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) Article 50 imposes
transparency duties on providers and deployers of specified systems. The Commission's final
[Article 50 guidelines page](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems)
confirms that those obligations apply from **2 August 2026**.

The Commission's
[Article 50 FAQ](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)
defines a provider as a person or body that develops or has an AI system developed and places it on
the EU market or puts it into service under its own name or trademark, whether established in or
outside the EU. A free release can therefore still be in scope. Article 2(12) also makes clear that
the general free/open-source exclusion does not exempt systems covered by Article 50.

For Therapist, the proportionate working assumption is that the publisher may be the provider of
the downstream conversational system even though OpenAI supplies the underlying model. This should
be treated as a documented self-assessment, not avoided by pointing only to the upstream model.

### Direct AI interaction: Article 50(1)

Providers of systems designed for direct two-way interaction with natural persons must ensure that
people are informed they are interacting with AI, unless that is obvious. The Commission says the
exception should be interpreted restrictively and that notice must be clear, distinguishable, and
provided from the start of the first interaction.

Therapist should therefore preserve an explicit AI identity in setup, CLI consent, Telegram consent,
and `/status`. This is a narrow, proportionate control and should be release evidence before
2 August 2026. It is stronger than relying on the repository name, a README disclaimer, or a user's
general familiarity with chatbots.

### Generated-content marking: Article 50(2)

Article 50(2) separately requires providers of systems generating synthetic audio, image, video, or
text to make outputs machine-readable and detectable as AI-generated, subject to its stated
technical-feasibility and assistive-editing limits. The Commission's
[quick facts](https://digital-strategy.ec.europa.eu/en/factpages/quick-facts-transparency-rules-ai-systems)
and FAQ state that:

- the requirement can cover text and applies to systems placed on the market for free;
- source code and certain machine-to-machine or closed-loop outputs fall outside scope;
- open-source status alone does not remove Article 50;
- systems placed on the market before 2 August 2026 have a limited transition for Article 50(2)
  marking until **2 December 2026**; this does not postpone Article 50(1) interaction disclosure.

The official sources do not justify assuming that terminal text is automatically exempt, nor do
they establish from this repository review whether marking supplied by an upstream model survives
the downstream CLI and Telegram transports. The proportionate action is to:

1. ship and retain explicit visible AI identity now;
2. record the system/provider and inherited-marking assessment;
3. test what detectable marking, if any, the upstream provider supplies;
4. select an Article 50(2) implementation or documented exception by the applicable transition
   deadline.

This is an upcoming technical/legal work item, but not a basis for describing a 23 July 2026
prerelease as unlawful before Article 50 applies.

Article 50(3) biometric emotion-recognition disclosure is not triggered merely because a text agent
discusses emotions: that provision concerns defined emotion-recognition systems based on biometric
data. Article 50(4) public-interest publication labelling is not ordinarily triggered by a private
single-user reply, and natural persons acting purely personally and non-professionally are excluded
as deployers. Those conclusions must be revisited if the product adds biometrics or publishes
generated content.

## Proportionate release checklist

Before the first prerelease:

- keep the public and in-product non-medical intended-purpose wording consistent;
- retain explicit AI identity and non-human-monitoring disclosure before first input;
- retain accurate CLI and Telegram data-flow disclosure and affirmative consent;
- retain local export and deletion, encrypted storage, separate key, and allowlisting;
- tell Telegram operators to set the custom `PRIVACY.md` URL in BotFather;
- ensure `/privacy` remains available and says local deletion does not delete Telegram messages;
- record the publisher/installer/operator/provider role split and the no-telemetry fact;
- record a DPIA screening conclusion and the changes that force re-screening;
- record the Article 50 provider/marking decision and its 2 August/2 December 2026 deadlines;
- avoid broad compliance, clinical safety, efficacy, endorsement, or regulatory-approval claims.

Not required by the reviewed sources as a gate for this exact alpha:

- publishing a personal email address;
- creating a special confidential privacy mailbox for conversation data the publisher never
  receives;
- commissioning a full external DPIA regardless of actual scale and roles;
- obtaining an external MDR opinion for stable, consistently non-medical wellness software;
- waiting for a regulator to approve an open-source prerelease.

## Reassessment triggers

Repeat this assessment before any:

- hosted or SaaS operation;
- publisher telemetry, support access, logging, or central inference;
- multi-user, organisation, employer, healthcare, or minor use;
- payment, donations tied to service, advertising, or other regular economic activity;
- medical, diagnostic, symptom-monitoring, treatment, alleviation, clinical, or efficacy claim;
- biometric input or emotion recognition based on biometric data;
- public publication of generated content;
- material provider, data location, retention, or transfer change;
- change to Telegram's Bot Platform terms, GDPR/EDPB guidance, MDR/MDCG guidance, or the AI Act and
  its implementing guidance.

## Primary official sources

- [Telegram Bot Platform Developer Terms](https://telegram.org/tos/bot-developers)
- [Telegram botInfo privacy-policy behavior](https://core.telegram.org/constructor/botInfo)
- [Telegram Privacy Policy](https://telegram.org/privacy)
- [GDPR, Regulation (EU) 2016/679](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679)
- [European Commission: application of the GDPR](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/application-gdpr_en)
- [European Commission: controllers and processors](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/obligations/controllerprocessor/what-data-controller-or-data-processor_en)
- [EDPB Guidelines 07/2020 on controller and processor concepts](https://www.edpb.europa.eu/documents/guideline/guidelines-072020-on-the-concepts-of-controller-and-processor-in-the-gdpr_en)
- [European Commission: legal grounds and special-category conditions](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/legal-grounds-processing-data_en)
- [European Commission: when a DPIA is required](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/obligations/when-data-protection-impact-assessment-dpia-required_en)
- [Italian Garante: Article 35(4) DPIA list, decision no. 467 of 11 October 2018](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9058979)
- [MDCG 2019-11 rev.1: software qualification and classification](https://health.ec.europa.eu/document/download/b45335c5-1679-4c71-a91c-fc7a4d37f12b_en?filename=mdcg_2019_11_en.pdf)
- [AI Act, Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [European Commission: final Article 50 guidelines](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems)
- [European Commission: Article 50 FAQ](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)
- [European Commission: Article 50 quick facts](https://digital-strategy.ec.europa.eu/en/factpages/quick-facts-transparency-rules-ai-systems)
