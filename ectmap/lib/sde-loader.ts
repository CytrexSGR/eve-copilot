import { createInterface } from 'readline';
import { createReadStream } from 'fs';
import { join } from 'path';

export interface SDERecord {
  _key: number;
  [key: string]: unknown;
}

const SDE_DATA_PATH = join(process.cwd(), 'public', 'sde');

/**
 * Get a readable stream for a file from the public/sde directory
 */
function getFileStream(filename: string): NodeJS.ReadableStream {
  const filePath = join(SDE_DATA_PATH, filename);
  return createReadStream(filePath, { encoding: 'utf-8' });
}

/**
 * Load all records from a JSONL file into memory
 * Use for small files like regions, constellations, systems
 * Optional filter predicate to reduce memory usage during streaming
 */
export async function loadAllRecords<T extends SDERecord>(
  filename: string,
  filter?: (record: T) => boolean
): Promise<Map<number, T>> {
  const records = new Map<number, T>();
  const fileStream = getFileStream(filename);

  const rl = createInterface({
    input: fileStream,
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    if (line.trim()) {
      const record = JSON.parse(line) as T;
      if (!filter || filter(record)) {
        records.set(record._key, record);
      }
    }
  }

  return records;
}

/**
 * Stream and filter records from a JSONL file
 * Use for large files like planets, moons when you only need specific records
 */
export async function findRecords<T extends SDERecord>(
  filename: string,
  predicate: (record: T) => boolean
): Promise<T[]> {
  const results: T[] = [];
  const fileStream = getFileStream(filename);

  const rl = createInterface({
    input: fileStream,
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    if (line.trim()) {
      const record = JSON.parse(line) as T;
      if (predicate(record)) {
        results.push(record);
      }
    }
  }

  return results;
}

/**
 * Find a single record by key
 */
export async function findRecordByKey<T extends SDERecord>(
  filename: string,
  key: number
): Promise<T | null> {
  const fileStream = getFileStream(filename);

  const rl = createInterface({
    input: fileStream,
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    if (line.trim()) {
      const record = JSON.parse(line) as T;
      if (record._key === key) {
        return record;
      }
    }
  }

  return null;
}
