# Provider data and policy matrix — 2026-07-23

## Purpose and status

This note records the current official terms, data handling, and safety-policy boundaries for the
external services Therapist actually exposes. It is a release decision aid, not legal advice or a
declaration of compliance. Provider terms and product behavior can change without a Therapist
release; every link and decision must be rechecked before each release.

`not established` means that the reviewed first-party source does not make the point clearly enough
to support a public claim. It does not mean that the opposite is true.

## Fixed alpha assumptions

- Product and repository name: **Therapist**.
- Publisher: **Matteo Dante**, acting as an individual.
- Free, non-commercial, adult-only alpha.
- No PyPI publication, SaaS, donations, sponsorship, hosted inference, central accounts, or
  maintainer-controlled API keys.
- Each user runs one local installation and supplies any remote-provider credentials and Telegram
  bot token.
- The publisher does not receive conversation content through the normal product path.
- No personal email address will be published. Public issues reject personal data and GitHub private
  vulnerability reporting handles confidential security reports.
- The intended use is self-reflection and mental wellbeing, not therapy, diagnosis, medical advice,
  treatment, clinical practice, or emergency monitoring.

These assumptions limit the decision. A hosted service, organizational deployment, minors, payment,
telemetry, central inference, or clinical positioning requires a new matrix.

## Data-flow baseline

Remote conversation providers receive the current message and selected conversation history,
structured memory, archive excerpts, tool inputs, and tool outputs needed for the run. This can
predictably contain mental-health information and therefore special-category health data under the
GDPR. It is not an unexpected edge case.

The transports and download services differ:

- Telegram receives the text sent to and from the bot before Therapist stores it locally.
- Hugging Face Hub is used only to download a pinned embedding-model revision; conversation text is
  embedded on the user's device.
- Ollama is local only if the selected model is local and Ollama cloud features are disabled.

Local Fernet encryption protects Therapist's SQLite files. It does not change what an external
provider receives, its retention, its legal role, or its terms.

## Release decision summary

| Service | Initial decision | Conditions or blocker |
| --- | --- | --- |
| OpenAI API through PydanticAI | **Hold** | Responses storage is disabled and tested; resolve standard-DPA treatment of intentionally sensitive data and remain strictly non-medical |
| Anthropic API | **Disable for alpha** | Therapy and mental health are a high-risk use case requiring qualified professional review; standard DPA lists no special-category data |
| Google Gemini Developer API | **Disable for alpha pending review** | EEA API clients require Paid Services; terms are for professional/business use and prohibit clinical/medical-advice/device uses |
| Ollama local | **Allow conditionally** | Loopback is enforced; identify local models and review each model's license and safety behavior |
| Personal ChatGPT Codex OAuth | **Allow experimentally by publisher decision** | Hermes Agent provides an open-source implementation precedent; independent backend use is still not an OpenAI API contract, API retention and DPA claims do not apply, and compatibility or availability is not promised |
| Telegram Bot API | **Allow for the self-hosted alpha** | Cloud and deletion disclosures, a stable privacy URL, `/privacy`, and per-operator BotFather setup are documented |
| Hugging Face Hub model download | **Allow** | Download is pinned and verified; telemetry and implicit credentials are disabled and runtime loads are local-only |
| OpenRouter technical override | **Unsupported for alpha** | Aggregator plus variable downstream provider; the public DPA does not cover this individual non-commercial use and does not intend sensitive-data processing |
| Arbitrary custom PydanticAI model | **Unsupported escape hatch** | No privacy, residency, retention, training, DPA, or policy claim can be made |

“Allow” means compatible with these release assumptions after the listed controls. It does not mean
the service is clinically safe, GDPR compliant, or endorsed for mental-health use.

## OpenAI API through PydanticAI

### Applicable product and terms

The `openai:` model prefix resolves to PydanticAI's `OpenAIResponsesModel` and the OpenAI Responses
API at `https://api.openai.com/v1`. This is the API product, governed by the OpenAI Services
Agreement, Service Terms, Usage Policies, and incorporated DPA—not the consumer ChatGPT terms.

Sources:

- [PydanticAI OpenAI provider](https://pydantic.dev/docs/ai/models/openai/)
- [OpenAI Services Agreement](https://openai.com/policies/services-agreement/)
- [OpenAI Service Terms](https://openai.com/policies/service-terms/)
- [OpenAI Usage Policies](https://openai.com/policies/usage-policies/)
- [OpenAI Data Processing Addendum](https://cdn.openai.com/pdf/openai-data-processing-addendum.pdf)

### Training and retention

- API Customer Content is not used to develop or improve OpenAI services by default unless the
  customer explicitly agrees or opts in
  ([Services Agreement §4.2](https://openai.com/policies/services-agreement/);
  [API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)).
- Default abuse-monitoring logs can contain prompts, responses, and derived classifier data and are
  retained for up to 30 days, unless longer retention is legally required
  ([API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)).
- The Responses API stores application state for at least 30 days by default. PydanticAI confirms
  that OpenAI stores responses by default and that `openai_store=False` disables that response
  storage
  ([PydanticAI OpenAI provider](https://pydantic.dev/docs/ai/models/openai/#referencing-earlier-responses);
  [API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)).
- Zero Data Retention and Modified Abuse Monitoring require OpenAI approval and additional
  requirements. They must never be implied from `store=false`
  ([API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)).

**Implemented technical control:** both the experimental Codex adapter and ordinary `openai:`
provider set `openai_store=False`; the deterministic suite verifies the ordinary provider setting,
and both conversation and consolidation share that model instance. This disables Responses
application-state storage but does not disable abuse-monitoring retention.

### GDPR role, sensitive data, regions, and subprocessors

The Services Agreement incorporates the DPA when the API processes personal data. The DPA generally
places the customer as controller and OpenAI as processor for Customer Data, with SCC mechanisms and
listed subprocessors.

However, Schedule 1 of the current DPA says sensitive data is not intended to be transferred unless
it appears unexpectedly in unstructured user data. Therapist predictably sends mental-health
content. Standard contractual coverage for this intended special-category use is therefore
**not established**. Do not claim that the standard DPA makes Therapist's health-data flow GDPR
compliant without provider clarification and qualified legal review.

The default global API endpoint does not establish EU-only processing. OpenAI documents regional
storage and, for some regions, processing only for specifically configured projects; non-US regions
require approved abuse-monitoring controls and a Zero Data Retention amendment. The current
Therapist configuration does not select such a project or endpoint.

Sources:

- [OpenAI DPA](https://cdn.openai.com/pdf/openai-data-processing-addendum.pdf)
- [OpenAI API data residency and retention controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)
- [OpenAI API subprocessor list](https://openai.com/policies/sub-processor-list/)

### Medical, high-stakes, and self-harm policy

OpenAI prohibits:

- tailored medical advice requiring a license without appropriate licensed-professional involvement;
- automated high-stakes medical decisions without human review;
- promotion or facilitation of suicide, self-harm, or disordered eating.

General supportive or reflective conversation is not an official approval of this product.
Therapist must remain on the wellbeing side of the boundary and pass provider-specific safety tests.

Source: [OpenAI Usage Policies](https://openai.com/policies/usage-policies/).

### Public claims

The project may say:

- “The OpenAI API does not use API Customer Content to train models by default unless the customer
  opts in.”
- “OpenAI may retain content in abuse-monitoring logs for up to 30 days.”

It must not say:

- zero retention, EU-only processing, HIPAA readiness, GDPR compliance, or suitability for health
  data;
- “OpenAI does not store your conversations” without both disabling Responses storage and explaining
  abuse-monitoring exceptions;
- OpenAI endorses, validates, or permits Therapist as a medical or therapeutic product.

## Anthropic API

### Applicable product and terms

Individuals and hobbyists may use the API, but Anthropic states that the Commercial Terms apply even
to them. The API is distinct from Claude's consumer products.

Sources:

- [Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms)
- [Anthropic: individual API use](https://support.anthropic.com/en/articles/8987200-can-i-use-the-anthropic-api-for-individual-use)
- [Anthropic Usage Policy](https://www.anthropic.com/legal/aup)

### Training and retention

- Anthropic may not train models on API Customer Content under the Commercial Terms; explicit
  feedback or a separate opt-in program can change that
  ([Commercial Terms §B](https://www.anthropic.com/legal/commercial-terms);
  [commercial model-training explanation](https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training)).
- API inputs and outputs are normally deleted from backend systems within 30 days. Longer retention
  can apply to customer-controlled features, separate agreements, legal requirements, and policy
  enforcement
  ([commercial retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)).
- If automated systems flag a policy violation, Anthropic states that inputs and outputs can be
  retained for up to two years and trust-and-safety classification scores for up to seven years.
  Feedback data can be retained for five years
  ([commercial retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)).

### GDPR role, sensitive data, regions, and subprocessors

The DPA identifies the customer as controller and Anthropic as processor, incorporates controller-
processor SCCs, and identifies Anthropic Ireland for EEA customers. Anthropic uses listed
subprocessors and provides a change-notice mechanism. Anthropic states that ordinary API data is
stored in the United States and that operational processing may also occur in Europe, Asia, and
Australia; EU-only processing is not the default.

The same DPA's processing schedule states that special categories of personal data are **none**.
Because Therapist predictably processes mental-health information, contractual suitability is
**not established**. Do not claim that the standard Anthropic DPA covers Therapist's expected health
data without a written clarification or amendment.

Sources:

- [Anthropic Data Processing Addendum](https://www.anthropic.com/legal/data-processing-addendum)
- [Anthropic subprocessors](https://www.anthropic.com/subprocessors)
- [Anthropic server locations](https://privacy.claude.com/en/articles/7996890-where-are-your-servers-located-do-you-host-your-models-on-eu-servers)

### Mental-health and self-harm policy

Anthropic's Usage Policy expressly classifies therapy, mental health, patient care, medical
diagnosis, and other medical guidance as “High-Risk Use Cases.” When advice, recommendations, or
subjective decisions are presented directly to consumers, a qualified professional in the field
must review the content before it is disseminated or finalized. AI use must also be disclosed at the
beginning of each session. Wellness advice such as general stress or sleep advice is excluded from
that high-risk category.

The policy also prohibits facilitating or glamorizing suicide, self-harm, disordered eating, and
harmful exercise, and requires every consumer-facing chatbot to disclose that it is AI.

Source: [Anthropic Usage Policy](https://www.anthropic.com/legal/aup).

### Release decision and claims

Therapist has no qualified professional reviewing every reply. Its current name, case formulation,
personalized intervention, and “therapeutic” behavior make it unsafe to assume that every output is
mere wellness advice. Keep Anthropic out of the guided setup and support claim unless Anthropic or
qualified counsel confirms that the implemented scope is outside the high-risk category and the
health-data contract issue is resolved.

The project may accurately describe Anthropic's default no-training and 30-day deletion rules, with
the enforcement exceptions. It must not claim zero retention, EU-only processing, health-data DPA
coverage, or provider approval.

## Google Gemini Developer API

### Applicable product and terms

The `google:` prefix uses the Gemini Developer API, not Vertex AI. The Gemini API Additional Terms
apply with the Google APIs Terms. They say:

- the APIs are for developers building for professional or business purposes, not consumer use;
- the API customer must be at least 18 and must not make an API client directed to or likely to be
  used by under-18s;
- an API client made available in the EEA, Switzerland, or UK may use only Paid Services.

The adult-only assumption aligns with the age rule. Compatibility between a personal,
consumer-facing local wellbeing app and the professional/business-purpose restriction is
**not established**. Because the publisher and expected users are in the EEA, unpaid Gemini quota is
not an acceptable release path.

Sources:

- [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- [PydanticAI Google provider](https://pydantic.dev/docs/ai/models/google/)

### Training and retention

- Outside the EEA/Switzerland/UK, Google can use unpaid-service inputs and outputs to improve
  products and models, and human reviewers may inspect them. Google says not to submit personal,
  sensitive, or confidential information to Unpaid Services
  ([Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)).
- For Paid Services, Google says prompts and responses are not used to improve products and are
  processed under its processor DPA
  ([Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)).
- Google retains prompts, context, and outputs for abuse monitoring for 55 days. Automated systems
  scan API usage, and authorized personnel may review flagged content. These logs are not used to
  train or fine-tune models except policy-enforcement systems
  ([Gemini API abuse monitoring](https://ai.google.dev/gemini-api/docs/usage-policies)).
- Optional developer-owned API logging for billing-enabled projects has a default maximum retention
  window of 55 days, configurable to 7, 14, 28, or 55 days. These logs are separate from Google's
  abuse-monitoring logs. Sharing a dataset or feedback with Google can permit model improvement
  ([Gemini API logging and sharing](https://ai.google.dev/gemini-api/docs/logs-policy)).

### GDPR, regions, and subprocessors

Paid prompts and responses are covered by Google's DPA for products where Google is a processor.
Account, billing, usage, safety-filter, and technical data remain under controller-controller terms.
Google says paid prompt and response data may be stored transiently or cached in any country where
Google or its agents maintain facilities. EU-only processing is therefore **not established**.

Use the current Google processor DPA and subprocessor information for a legal review; do not infer
that general Google Cloud residency controls apply to the Gemini Developer API.

Sources:

- [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- [Google Cloud Data Processing Addendum](https://cloud.google.com/terms/data-processing-addendum)
- [Google Cloud subprocessors](https://cloud.google.com/terms/subprocessors)

### Medical, high-stakes, and self-harm policy

The Gemini API Additional Terms prohibit using the service:

- in clinical practice;
- to provide medical advice;
- in a manner overseen by or requiring medical-device regulatory clearance or approval.

Google's Generative AI Prohibited Use Policy also prohibits facilitating self-harm, making automated
high-risk healthcare decisions with materially detrimental effects without human supervision, and
misleading health expertise or harmful health claims.

Sources:

- [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- [Google Generative AI Prohibited Use Policy](https://policies.google.com/terms/generative-ai/use-policy)

### Release decision and claims

Keep Gemini out of the guided setup and support claim until all of the following are documented:

1. a billing-enabled Paid Services project is required and verified for EEA use;
2. the professional/business-purpose restriction is reconciled with the personal local alpha;
3. behavior and claims are demonstrated to remain outside medical advice, clinical practice, and
   medical-device scope;
4. the selected preview model's release stability is acceptable.

Do not generalize “no training” from Paid Services to unpaid usage outside the EEA, or claim EU-only
processing, no human review, zero retention, or medical suitability.

## Ollama local

### Applicable product and data handling

Ollama's API is served locally at `http://localhost:11434` by default and requires no authentication.
Ollama states that it does not see prompts, responses, or local model interactions when inference is
local. Its privacy policy separately permits limited device, usage, diagnostic, and model-download
metadata that does not include prompt or response content.

Ollama can also run cloud models through the same local endpoint. For cloud-hosted models, Ollama
states that prompts and responses are processed transiently, not stored or logged, and not used for
training. A public DPA, subprocessor commitment, exact transient duration, and regional-processing
guarantee for Ollama Cloud are **not established**.

Sources:

- [Ollama API introduction](https://docs.ollama.com/api/introduction)
- [Ollama Privacy Policy](https://ollama.com/privacy)
- [Ollama Terms](https://ollama.com/terms)
- [Ollama authentication](https://docs.ollama.com/api/authentication)

### Release conditions

Allow `ollama:` only as a strictly local option:

- require the loopback base URL and reject a remote or network-exposed endpoint;
- require `disable_ollama_cloud: true` or `OLLAMA_NO_CLOUD=1` and verify the running server reports
  cloud disabled;
- reject cloud model identifiers;
- explain that the local API has no authentication and must not be exposed to the network;
- review and show the selected model's own license, model card, data provenance, and safety limits;
- run the same bilingual safety suite against each advertised local model.

Ollama is a runner, not a safety certification. Training provenance, health suitability, and
self-harm behavior are model-specific and otherwise **not established**.

Source: [Ollama FAQ: privacy, cloud disablement, and bind address](https://docs.ollama.com/faq).

### Public claims

After those controls, the project may say “conversation inference stays on this device when a local
Ollama model is selected.” It must not say that all `ollama:` models are local, safe, private,
licensed for every use, or equivalent in behavior.

## Experimental personal ChatGPT Codex OAuth

### Applicable product and terms

This adapter authenticates a personal ChatGPT Plus/Pro account through the Codex device-code flow and
calls the ChatGPT-backed Codex endpoint. It is not an OpenAI API key integration. The applicable
baseline is the consumer Europe Terms of Use for an EEA user, the Service Terms for Codex, the
Privacy Policy, Data Controls, and universal Usage Policies.

OpenAI documents ChatGPT authentication for official Codex clients, programmatic control through
the Codex SDK, and broader Codex use cases. Those materials do not establish that an independent
third-party client may use the direct Codex backend as a conversation provider under a personal
subscription.

Sources:

- [OpenAI Codex app-server authentication](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md#auth-endpoints)
- [OpenAI: Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540)
- [Hermes Agent provider documentation](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/providers.md)
- [Hermes Agent authentication implementation](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/auth.py)
- [OpenAI Europe Terms of Use](https://openai.com/policies/terms-of-use/)
- [OpenAI Service Terms](https://openai.com/policies/service-terms/)
- [OpenAI Privacy Policy](https://openai.com/policies/privacy-policy/)

### Training, retention, DPA, and regions

- Consumer ChatGPT and Codex content may be used for model improvement unless the user turns off the
  account's model-improvement control. Codex also has separate controls for sharing full
  environments
  ([OpenAI model-improvement explanation](https://help.openai.com/en/articles/5722486-api-data-usage-policies);
  [Data Controls FAQ](https://help.openai.com/en/articles/7730893-data-controls-faq)).
- The project's `store=false` request parameter is not evidence that ChatGPT consumer data follows
  API Zero Data Retention. Exact storage, abuse-review retention, and deletion behavior for this
  direct backend integration are **not established**.
- The API Services Agreement, API DPA, API 30-day abuse-log statement, API regional projects, and API
  subprocessor promises must not be applied to this consumer subscription.
- OpenAI Ireland is the controller for EEA consumer data, and the consumer privacy policy permits
  processing in multiple jurisdictions using valid transfer mechanisms. There is no customer-
  processor DPA for an ordinary Plus/Pro consumer account
  ([OpenAI Privacy Policy](https://openai.com/policies/privacy-policy/)).

The universal medical, high-stakes, and self-harm restrictions described in the OpenAI section also
apply.

### Release decision and claims

The publisher selected Codex OAuth for the first alpha and accepts the compatibility and availability
risk, following the public Hermes Agent implementation precedent. Keep the code and public wording
clearly experimental. Reassess this decision if OpenAI changes the flow, blocks the client, publishes
contrary terms, or before any hosted or commercial use.

The project may say only that it uses an experimental ChatGPT-managed Codex OAuth flow. It must not
call this “the OpenAI API,” promise API privacy controls, claim subscription authorization for
mental-health use, or imply OpenAI endorsement.

## Telegram Bot API

### Applicable terms and data handling

Telegram bots are third-party applications governed by the Telegram Terms, Privacy Policy, and Bot
Platform Developer Terms. Telegram states that ordinary cloud-chat messages are stored on its
servers so they remain available across devices. End-to-end encryption applies to Secret Chats;
bots do not operate in Secret Chats. “Private chat” therefore means one-to-one and allowlisted, not
end-to-end encrypted or visible only to Therapist.

Telegram's Bot Developer Terms require every bot to have an easily accessible privacy policy
describing the data stored, collection method, and purpose. A custom policy must be configured in
BotFather when Telegram's generic standard policy does not accurately cover the bot. Those terms
also require deletion when requested, no longer necessary, the bot stops operating, or law requires
it.

Sources:

- [Telegram Privacy Policy](https://telegram.org/privacy)
- [Telegram Bot Platform Developer Terms](https://telegram.org/tos/bot-developers)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Training, retention, roles, regions, and DPA

- Telegram training on bot conversation content: **not established**.
- A fixed server-side retention period for ordinary bot cloud-chat messages after product-local
  deletion: **not established**.
- Telegram states that cloud-chat data and encryption keys are held across data centers in different
  jurisdictions. EU-only storage or processing for bot chats: **not established**.
- A public bot-specific controller-processor DPA under which Telegram acts as Therapist's processor:
  **not established**.
- Telegram and the person operating the bot have separate responsibilities. Because every user
  creates and runs a personal bot, the final controller/household-role allocation requires a factual
  legal analysis; the publisher does not receive the bot messages in the normal architecture.

### Policy and release conditions

Telegram publishes no official medical, high-stakes, or self-harm suitability promise for the Bot
API. It is only a transport and must not be treated as a safety system.

Before enabling Telegram in the public alpha:

1. publish an accurate privacy/data-flow policy under Matteo Dante's name;
2. provide a stable policy URL that each user can configure for the bot in BotFather;
3. disclose before consent that Telegram cloud stores messages and is not end-to-end encrypted;
4. identify every remote model recipient separately;
5. provide local correction, export, and deletion controls;
6. explain that local `/forget` or `delete-data` does not itself erase Telegram's cloud copies and
   document how the user deletes both Telegram messages/chat and local Therapist data;
7. retain the allowlist, private-chat-only enforcement, encryption at rest, and explicit,
   revocable consent.

Allowed public wording: “optional private, single-user, allowlisted Telegram bot.” Disallowed
generalization: “end-to-end encrypted,” “only stored locally,” “confidential,” or “Telegram is a
processor under our DPA.”

## Hugging Face Hub: embedding-model download only

### Applicable flow

Setup downloads the pinned
[`Qwen/Qwen3-Embedding-0.6B`](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) revision from the
Hugging Face Hub. The model card and repository identify the model license as Apache-2.0.
Conversation and memory text are embedded locally after installation; they are not API inference
inputs to Hugging Face.

Hub downloads still disclose ordinary network information such as IP address and request metadata.
Hugging Face libraries can emit usage telemetry by default; the official control is
`HF_HUB_DISABLE_TELEMETRY=1`. A logged-in Hub token may also be sent implicitly unless
`HF_HUB_DISABLE_IMPLICIT_TOKEN=1` is used. Runtime network checks can be prevented with
`HF_HUB_OFFLINE=1`.

Sources:

- [Hugging Face Hub environment variables](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables)
- [Hugging Face Privacy Policy](https://huggingface.co/privacy)
- [Hugging Face Terms of Service](https://huggingface.co/terms-of-service)
- [Pinned embedding model](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)

### Training, retention, regions, DPA, and safety

- Training on Therapist conversations: not applicable when the Hub is used only for model download.
- Hub request/telemetry retention, exact processing regions, and subprocessors for an anonymous model
  download: **not established** in a form that supports a more specific product claim.
- Hugging Face's customer DPA is an Enterprise commitment; it should not be generalized to anonymous
  public Hub downloads.
- The Hub and embedding model do not generate therapeutic replies. Medical, high-stakes, and
  self-harm output policy is therefore not applicable to this download path.

### Release conditions and claims

Allow the download path after:

- setting `HF_HUB_DISABLE_TELEMETRY=1` before importing Hugging Face libraries;
- avoiding implicit Hub credentials for the public model;
- pinning and checksum-verifying the exact model revision;
- forcing offline mode for chat and Telegram after setup/verification;
- documenting that setup makes a network request and normal network metadata reaches Hugging Face.

The project may say: “The embedding model is downloaded once from Hugging Face and runs locally.”
It must not say that installation is anonymous, sends no metadata, or is covered by an Enterprise
DPA.

## OpenRouter API

### Applicable product and provider chain

The current setup presents `openrouter:anthropic/claude-sonnet-4.6` as a first-class choice.
OpenRouter is an aggregator, not the first-party Anthropic API: requests pass through OpenRouter and
one selected or dynamically routed model-provider endpoint. OpenRouter's Terms and Privacy Policy
apply to its layer; the selected endpoint's “Model Terms” and policies also apply. First-party
Anthropic contractual or data claims must not be inherited merely because the model is Claude.

Sources:

- [OpenRouter Terms](https://openrouter.ai/terms)
- [OpenRouter Privacy Policy](https://openrouter.ai/privacy/)
- [OpenRouter provider logging](https://openrouter.ai/docs/guides/privacy/provider-logging)

### Training, retention, and abuse handling

- OpenRouter says prompt and response retention at its own layer is opt-in. Private input/output
  logging and OpenRouter's use of content for product improvement are off by default.
- OpenRouter still retains per-request metadata. It also samples some prompts for anonymous topic
  categorization using a ZDR model when content-use opt-in is off. The fixed retention period for
  request metadata and anonymous categories is **not established**.
- Downstream providers have endpoint-specific training, retention, abuse-review, and human-review
  rules. OpenRouter's default routing does not filter providers by retention. Training can be
  denied through account or per-request data-policy filters.
- OpenRouter supports per-request `provider.zdr=true`. It then routes only to endpoints it classifies
  as ZDR, but allows in-memory provider caching under its ZDR definition. ZDR does not cover optional
  third-party plugins or tools.

Sources:

- [OpenRouter data collection](https://openrouter.ai/docs/guides/privacy/data-collection)
- [OpenRouter provider logging](https://openrouter.ai/docs/guides/privacy/provider-logging)
- [OpenRouter zero-data-retention controls](https://openrouter.ai/docs/guides/features/zdr)

### GDPR roles, sensitive data, regions, and subprocessors

OpenRouter's public DPA identifies a customer as controller and OpenRouter as processor, includes
controller-to-processor SCCs, and lists subprocessors through its trust center. However:

- the Terms incorporate the DPA for an organization or commercial/for-profit use, while this alpha
  is published and used by an individual on a non-commercial basis;
- the DPA says OpenRouter is not required to process sensitive data unless explicitly agreed and its
  schedule says no sensitive or special-category processing is intended;
- each downstream model provider is an additional recipient governed by its endpoint-specific
  terms, and the user is responsible for selecting and reviewing those terms.

Therefore DPA coverage and contractual permission for Therapist's expected mental-health data are
**not established** for this release. OpenRouter's US infrastructure and ordinary service may
involve transfers outside the EEA using adequacy mechanisms or SCCs. EU-only routing exists only for
enterprise customers by request at a separate EU base URL; it does not apply to this configuration.
The exact downstream region and processor/subprocessor role vary by route.

Sources:

- [OpenRouter Data Processing Agreement](https://openrouter.ai/data-processing-agreement)
- [OpenRouter Privacy Policy](https://openrouter.ai/privacy/)
- [OpenRouter enterprise EU routing](https://openrouter.ai/docs/guides/privacy/provider-logging#enterprise-eu-in-region-routing)

### Medical, high-stakes, and self-harm policy

OpenRouter makes no warranty that output is suitable for regulated, high-risk, safety-critical,
medical, or customer-facing use and places responsibility for human review and safeguards on the
user. A dedicated OpenRouter mental-health or self-harm policy is **not established**. The selected
model provider's policies remain independently relevant; for the configured Claude model, the
Anthropic high-risk mental-health restriction cannot be bypassed by routing through OpenRouter.

Source: [OpenRouter Terms §16](https://openrouter.ai/terms).

### Release decision and claims

Keep OpenRouter out of the guided setup and support claim. Reconsider only with a fixed endpoint, an
applicable sensitive-data agreement, enforced ZDR and no-training routing, documented region and
provider chain, and a complete safety-policy review for that exact endpoint.

The project may say that OpenRouter does not retain prompts or responses at its own layer by default,
subject to opt-ins and its categorization process. It must not claim end-to-end ZDR, no training, no
human review, EU-only processing, DPA coverage for health data, first-party Anthropic API treatment,
or medical suitability.

## Arbitrary PydanticAI model

The custom model-ID escape hatch can point to providers not reviewed here. Label it unsupported and
require a fresh, provider-specific disclosure. For it, training, retention, abuse review, regions,
DPA, subprocessors, and medical/self-harm policies are all **not established**.

## Cross-provider release requirements

Before any remote provider is enabled:

- [ ] Show the exact provider product, not only the model name.
- [ ] Require the user to accept that provider's current terms directly with their own credential.
- [ ] Show training default, retention, enforcement exceptions, external recipients, and transfer
      uncertainty before the first message.
- [ ] Do not equate “not used for training” with “not stored.”
- [ ] Do not equate `store=false` with zero data retention.
- [ ] Do not reuse API privacy claims for a consumer subscription or aggregator.
- [ ] Verify whether the provider's DPA expressly supports expected special-category health data.
- [ ] Keep medical advice, diagnosis, treatment, clinical decisions, and emergency monitoring out of
      prompts, claims, and behavior.
- [ ] Run provider-specific, bilingual, multi-turn safety evaluations on the exact model revision.
- [ ] Recheck policies when a preview model, endpoint, or provider changes.

## Recommended alpha configuration

The selected non-commercial adult-only release configuration is:

1. **Conversation:** the explicitly accepted experimental personal Codex OAuth path.
2. **Embedding:** pinned Hugging Face download during setup, telemetry disabled, then offline.
3. **Transport:** local CLI or one allowlisted private Telegram bot with the published policy and
   cloud-chat disclosure.
4. **Technical overrides:** other PydanticAI providers remain unsupported and are not advertised for
   the alpha.

This configuration does not make Therapist clinically validated or legally compliant by itself. It
does keep the public alpha's factual privacy claims within what the current official sources support.
