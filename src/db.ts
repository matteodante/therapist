import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { sqlite } from '@flue/runtime/node';
import { optionalEnv } from './shared/env.ts';

const filename = resolve(optionalEnv('FLUE_DB_PATH', './data/flue.db'));
mkdirSync(dirname(filename), { recursive: true });

export default sqlite(filename);
