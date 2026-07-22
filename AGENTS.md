# Development agent instructions

## Language and style

- Always respond to the user in Italian, concisely but completely.
- Write all repository documentation, comments, examples, fixtures, and evaluation scenarios in English.
- Keep Flue names, APIs, and technical terms in the form used by the official documentation.

## Required Flue documentation

Before creating or modifying code involving Flue, always retrieve and consult the current official guides at <https://flueframework.com/docs/>. Do not rely only on memory, local examples, or assumed APIs.

Consult at least the guide relevant to the change:

- project structure: <https://flueframework.com/docs/guide/project-layout/>
- agents: <https://flueframework.com/docs/guide/building-agents/>
- skills: <https://flueframework.com/docs/guide/skills/>
- tools: <https://flueframework.com/docs/guide/tools/>
- sandboxes: <https://flueframework.com/docs/guide/sandboxes/>
- routing and `app.ts`: <https://flueframework.com/docs/guide/routing/>
- agent API: <https://flueframework.com/docs/api/agent-api/>

When the current documentation differs from the Flue version pinned in `package.json`, also verify the installed types and effective APIs. Do not upgrade Flue or any other dependency without an explicit request.

## Required Flue structure

- Use `src/` as the canonical source directory.
- Keep agents directly in `src/agents/`, without nested agents. Use `lower-kebab-case.ts` filenames and a `default export` created with `defineAgent(...)`.
- Keep `src/app.ts` as the Hono composition point for middleware, health checks, and the `flue()` mount.
- Keep channels directly in `src/channels/`; every channel discovered by Flue must export the named `channel` binding.
- Use `src/workflows/` only for finite operations with an input and result, not for persistent conversations.
- Store long instructions in dedicated Markdown files and import them with the attribute supported by the installed Flue version.
- Store application Agent Skills in `src/skills/<skill-name>/SKILL.md`. The directory name must match the frontmatter `name`. Import skills with `with { type: 'skill' }` and register them in the agent configuration.
- Use a tool for bounded executable capabilities, a skill for reusable instructions and procedures, and a workflow for finite application-controlled work.

## Security boundaries

- Define tools with `defineTool`, clear names, Valibot input and output schemas, and `run({ input, signal })` according to the current APIs.
- Treat every model-selected input as untrusted. Trusted code must determine credentials, user identity, tenant, destination, and authorization limits.
- Preserve least privilege. Do not expand sandbox, shell, filesystem, network, or credential access without an explicit and documented need.
- Preserve the restricted sandbox and single-user Telegram constraint unless an explicit request includes a security review.
- Keep user-stated personal memory separate from assistant-generated process notes.

## Verification

After every material change, run checks proportional to the change. At minimum:

```bash
pnpm typecheck
pnpm test
```

For changes to agents, skills, routing, or packaging, also run Flue's native
build validation:

```bash
pnpm build
```

Use `pnpm run ci` for the complete pipeline. Do not use `pnpm ci`: in pnpm 11 it is an installation command alias and does not execute the `ci` script from `package.json`.

Do not declare a change complete unless the required checks have run. Clearly report any unavailable verification and its reason.

## Git workflow

- Commit completed work directly to `main` and push `main` to `origin`.
- Do not create feature branches or pull requests unless the user explicitly requests them.
