# Contributing

Therapist accepts contributions to code, documentation, evaluation, translation,
and protocol authoring.

## Before opening a pull request

```bash
pnpm install
pnpm check
pnpm build
```

## Clinical content

Changes to therapeutic skills must include:

1. source references;
2. intended population and scope;
3. indications and contraindications;
4. an executable evaluation case once the protected eval harness exists;
5. explicit uncertainty and stop conditions;
6. review status in the skill metadata.

Do not copy copyrighted manuals into the repository. Public availability does
not imply redistribution rights.

## Code principles

- Keep one primary agent.
- Prefer bounded application tools over broad capabilities.
- Never add host shell, unrestricted filesystem, browser, or generic network
  access to the model.
- Keep Telegram destination, user identity, credentials, and memory bank IDs in
  trusted application code rather than model-selected arguments.
- Preserve the distinction between the canonical transcript, structured
  user-confirmed records, and the derived semantic index.
- Avoid engagement-maximizing features.

## Commit style

Use concise imperative subjects, for example:

```text
Add collaborative formulation skill
Harden Telegram user allowlist
Document Hindsight deletion strategy
```
