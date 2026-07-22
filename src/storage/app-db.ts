import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { optionalEnv } from '../shared/env.ts';

const filename = resolve(optionalEnv('THERAPIST_APP_DB_PATH', './data/therapist-app.db'));
mkdirSync(dirname(filename), { recursive: true });

const db = new DatabaseSync(filename);
db.exec(`
  PRAGMA journal_mode = WAL;
  PRAGMA foreign_keys = ON;
  PRAGMA busy_timeout = 5000;

  CREATE TABLE IF NOT EXISTS telegram_updates (
    update_id INTEGER PRIMARY KEY,
    received_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS structured_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    note TEXT NOT NULL,
    evidence TEXT NOT NULL,
    created_at TEXT NOT NULL
  );

  CREATE INDEX IF NOT EXISTS structured_memories_user_created
  ON structured_memories (user_key, created_at DESC);

  CREATE VIRTUAL TABLE IF NOT EXISTS structured_memories_fts USING fts5(
    note,
    evidence,
    content = structured_memories,
    content_rowid = id
  );

  CREATE TRIGGER IF NOT EXISTS structured_memories_ai AFTER INSERT ON structured_memories BEGIN
    INSERT INTO structured_memories_fts(rowid, note, evidence)
    VALUES (new.id, new.note, new.evidence);
  END;

  CREATE TRIGGER IF NOT EXISTS structured_memories_ad AFTER DELETE ON structured_memories BEGIN
    INSERT INTO structured_memories_fts(structured_memories_fts, rowid, note, evidence)
    VALUES ('delete', old.id, old.note, old.evidence);
  END;
`);

const claimUpdate = db.prepare(`
  INSERT OR IGNORE INTO telegram_updates (update_id, received_at)
  VALUES (?, ?)
`);

const insertStructuredMemory = db.prepare(`
  INSERT INTO structured_memories (user_key, kind, note, evidence, created_at)
  VALUES (?, ?, ?, ?, ?)
`);

const recentStructuredMemories = db.prepare(`
  SELECT kind, note, evidence, created_at
  FROM structured_memories
  WHERE user_key = ?
  ORDER BY created_at DESC
  LIMIT 20
`);

const searchStructuredMemories = db.prepare(`
  SELECT memory.kind, memory.note, memory.evidence, memory.created_at
  FROM structured_memories_fts AS search
  JOIN structured_memories AS memory ON memory.id = search.rowid
  WHERE memory.user_key = ? AND structured_memories_fts MATCH ?
  ORDER BY bm25(structured_memories_fts), memory.created_at DESC
  LIMIT 20
`);

const deleteStructuredMemories = db.prepare(`
  DELETE FROM structured_memories WHERE user_key = ?
`);

export type StructuredMemory = {
  kind: string;
  note: string;
  evidence: string;
  createdAt: string;
};

export function claimTelegramUpdate(updateId: number): boolean {
  const result = claimUpdate.run(updateId, new Date().toISOString());
  return Number(result.changes) === 1;
}

export function recordStructuredMemory(
  userKey: string,
  kind: string,
  note: string,
  evidence: string,
): void {
  insertStructuredMemory.run(userKey, kind, note, evidence, new Date().toISOString());
}

function rowsToStructuredMemory(rows: unknown[]): StructuredMemory[] {
  return rows.map((row) => {
    const value = row as Record<string, unknown>;
    return {
      kind: String(value.kind),
      note: String(value.note),
      evidence: String(value.evidence),
      createdAt: String(value.created_at),
    };
  });
}

export function recallStructuredMemory(userKey: string, query: string): StructuredMemory[] {
  const terms = query.match(/[\p{L}\p{N}]{3,}/gu)?.slice(0, 8) ?? [];
  if (terms.length === 0) {
    return rowsToStructuredMemory(recentStructuredMemories.all(userKey));
  }

  const match = terms.map((term) => `"${term.replaceAll('"', '""')}"`).join(' OR ');
  const matches = rowsToStructuredMemory(searchStructuredMemories.all(userKey, match));
  return matches.length > 0
    ? matches
    : rowsToStructuredMemory(recentStructuredMemories.all(userKey));
}

export function clearStructuredMemory(userKey: string): number {
  const result = deleteStructuredMemories.run(userKey);
  return Number(result.changes);
}
