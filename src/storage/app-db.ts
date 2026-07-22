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
`);

const claimUpdate = db.prepare(`
  INSERT OR IGNORE INTO telegram_updates (update_id, received_at)
  VALUES (?, ?)
`);

export function claimTelegramUpdate(updateId: number): boolean {
  const result = claimUpdate.run(updateId, new Date().toISOString());
  return Number(result.changes) === 1;
}

export function closeAppDatabase(): void {
  db.close();
}
