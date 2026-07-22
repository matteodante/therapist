# Security policy

## Supported versions

Therapist is pre-1.0 research software. Only the latest commit on `main` is
supported.

## Reporting a vulnerability

Do not open public issues for vulnerabilities involving secrets, access
control, cross-user data exposure, memory disclosure, or Telegram webhook
verification. Contact the maintainers privately through GitHub Security
Advisories once the repository is published.

## Security assumptions

- One authorized Telegram user per deployment.
- No model-facing host shell, filesystem, browser, or arbitrary HTTP tools.
- Secrets are supplied only through environment variables.
- Telegram webhook requests are verified using an independent secret token.
- Flue canonical conversations and the Markdown memory vault are sensitive
  personal data.
- A future SaaS deployment requires tenant isolation, encryption, deletion
  workflows, audit logging, and a formal threat model before accepting users.

See [`docs/SECURITY_AND_PRIVACY.md`](docs/SECURITY_AND_PRIVACY.md).
