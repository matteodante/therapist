# Privacy and data flow

This notice describes the current self-hosted alpha. It is not a claim of GDPR or other regulatory
compliance. Reassess it whenever providers, transports, telemetry, hosting, users, or business model
change.

## Who operates the software

The person who installs Therapist operates their own single-user instance and chooses any model
provider and Telegram account. The repository maintainer does not receive conversations, memory, or
credentials during normal use. Data reaches the maintainer only when a user deliberately submits it
through a support, security, or contribution channel; those channels prohibit real conversations,
health information, credentials, and other personal data.

The public alpha is intended for adults using it privately for self-reflection. It is not intended
for organizations to deploy to patients, clients, employees, students, or other third parties.

## Local data

By default, application data is stored in `~/.therapist/`:

- `thera.db` contains conversation messages, model history, sessions, structured memory, case
  formulation, interventions, configuration, provider secrets, and the derived semantic index;
- `memory.key` contains the Fernet key used to encrypt sensitive SQLite payloads.

The directory is set to filesystem mode `0700` and the key to `0600` on platforms that implement
those permissions. Conversation content, memory content, summaries, configuration payloads, secrets,
and embedding vectors are encrypted. SQLite still exposes structural metadata such as record IDs,
roles, states, and timestamps.

Keeping the database and key on the same account protects a copied database without its key and
casual backups. It does not protect data from malware, a compromised operating-system account, a
process running as the user, screen capture, terminal history, or a backup containing both files.
Full-disk encryption and device security remain the user's responsibility.

The pinned embedding model is downloaded from Hugging Face and then runs locally. The shared model
cache is separate from the application database and contains model files, not conversation content.

## External recipients

The selected configuration determines where content goes:

| Mode | Content sent outside the device |
| --- | --- |
| Local Ollama model + terminal | No conversation content is intentionally sent to a model provider or transport |
| Remote PydanticAI model | Current messages, successful active-session model history, and bounded selected context are sent to the chosen provider |
| Experimental personal Codex OAuth | The same model input is sent through the user's ChatGPT Codex account under that product's terms |
| Telegram | Telegram receives incoming messages, outgoing replies, tool events, notices, and any local data the user asks to view; the selected model provider also receives model input |

Supported remote configurations currently include OpenAI, Anthropic, Google, OpenRouter, and a custom
PydanticAI model ID. Each service has its own retention, abuse-monitoring, training, subprocessors,
region, transfer, and deletion terms. Therapist does not control those terms and does not promise
zero retention. Review the selected provider's current terms before sending sensitive content.

Deleting local data does not delete data already retained by Telegram, a model provider, terminal
capture, exports, or backups.

## Retention, access, export, and deletion

The local archive is retained until the user removes it. Structured claims can be inspected,
confirmed, corrected, or forgotten. `thera export` produces a decrypted JSON export; an export written
to disk is plaintext and must be protected by the user. `thera delete-data` removes application
records from the active SQLite database but does not remove the encryption key, the empty database,
the shared embedding-model cache, external-provider records, exports, or backups.

There is no product telemetry, advertising, analytics, maintainer-controlled inference, or automatic
upload of crash reports in the current alpha.

## Support and security reports

Do not submit conversations, databases, exports, health information, credentials, identifiers, or
other personal data in a GitHub issue. Use synthetic reproductions. Report vulnerabilities through
[GitHub private vulnerability reporting](https://github.com/matteodante/therapist/security/advisories/new).
See [SUPPORT.md](SUPPORT.md) for the complete reporting boundary.

Questions about an external provider's data should be directed to that provider. Because the
maintainer does not hold normal application data, local access, export, correction, and deletion are
performed by the user through the application commands.
