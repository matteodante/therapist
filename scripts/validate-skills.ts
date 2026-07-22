import { readdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import yaml from 'js-yaml';

const skillsRoot = resolve('src/skills');
const entries = await readdir(skillsRoot, { withFileTypes: true });
let failed = false;

for (const entry of entries.filter((item) => item.isDirectory())) {
  const file = resolve(skillsRoot, entry.name, 'SKILL.md');
  const text = await readFile(file, 'utf8');
  const match = /^---\n([\s\S]*?)\n---\n([\s\S]+)$/m.exec(text);

  if (!match) {
    console.error(`✗ ${entry.name}: missing YAML frontmatter`);
    failed = true;
    continue;
  }

  const frontmatter = yaml.load(match[1]!) as Record<string, unknown>;
  const body = match[2]!;

  if (frontmatter.name !== entry.name) {
    console.error(`✗ ${entry.name}: frontmatter name must match directory`);
    failed = true;
  }

  if (typeof frontmatter.description !== 'string' || !frontmatter.description.trim()) {
    console.error(`✗ ${entry.name}: description is required`);
    failed = true;
  }

  if (typeof frontmatter.license !== 'string' || !frontmatter.license.trim()) {
    console.error(`✗ ${entry.name}: license is required`);
    failed = true;
  }

  const requiredHeadings = ['## When to use', '## Verification', '## Sources'];
  for (const heading of requiredHeadings) {
    if (!body.toLowerCase().includes(heading.toLowerCase())) {
      console.error(`✗ ${entry.name}: missing ${heading}`);
      failed = true;
    }
  }

  if (body.length > 12_000) {
    console.error(`✗ ${entry.name}: SKILL.md exceeds 12,000 characters`);
    failed = true;
  }

  console.log(`✓ ${entry.name}`);
}

process.exitCode = failed ? 1 : 0;
