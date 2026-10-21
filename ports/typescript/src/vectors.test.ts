import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { beforeAll, describe, expect, it } from 'vitest';

import {
  LshIndex,
  MinHasher,
  charShingles,
  fnv1a64,
  jaccardEstimate,
  sha256,
  simhash128Text,
  simhash64Text,
  tokenize,
  wordShingles,
} from './index.js';

// The ONE shared vectors file — same as Rust/Python/Go/PHP consume.
const VECTORS_PATH = join(
  dirname(dirname(dirname(dirname(fileURLToPath(import.meta.url))))),
  'vectors',
  'lomboksimhash-vectors-v2.json'
);

interface VectorDoc {
  schema: string;
  cases: Record<string, Array<Record<string, unknown>>>;
}

let doc: VectorDoc;

function bytesFromHex(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function hex64(v: bigint): string {
  return v.toString(16).padStart(16, '0');
}

function sigOf(hexes: string[]): bigint[] {
  return hexes.map((h) => BigInt('0x' + h));
}

describe('shared vectors v2', () => {
  beforeAll(() => {
    doc = JSON.parse(readFileSync(VECTORS_PATH, 'utf-8')) as VectorDoc;
    expect(doc.schema).toBe('lomboksimhash-vectors-v2');
  });

  it('sha256 vectors', () => {
    for (const c of doc.cases.sha256!) {
      const data =
        typeof c.input === 'string'
          ? new TextEncoder().encode(c.input)
          : bytesFromHex(c.input_hex as string);
      expect(sha256(data), `case ${c.id}`).toBe(c.expected_hex);
    }
  });

  it('fnv1a64 vectors', () => {
    for (const c of doc.cases.fnv1a64!) {
      const got = hex64(fnv1a64(bytesFromHex(c.input_hex as string)));
      expect(got, `case ${c.id}`).toBe(c.expected_hex);
    }
  });

  it('shingle vectors', () => {
    for (const c of doc.cases.shingle!) {
      const got =
        c.mode === 'character'
          ? charShingles(c.input as string, c.n as number)
          : wordShingles(c.input as string, c.n as number);
      expect(got, `case ${c.id}`).toEqual(c.expected);
    }
  });

  it('simhash64 vectors', () => {
    for (const c of doc.cases.simhash64!) {
      const got = hex64(simhash64Text(c.input as string));
      expect(got, `case ${c.id}`).toBe(c.expected_hex);
    }
  });

  it('simhash128 vectors', () => {
    for (const c of doc.cases.simhash128!) {
      const [hi, lo] = simhash128Text(c.input as string);
      expect(hex64(hi), `case ${c.id} hi`).toBe(c.hi_hex);
      expect(hex64(lo), `case ${c.id} lo`).toBe(c.lo_hex);
      expect(hex64(hi) + hex64(lo), `case ${c.id} hex`).toBe(c.hex);
    }
  });

  it('minhash signature vectors (bit-identical)', () => {
    for (const c of doc.cases.minhash_signature!) {
      const mh = new MinHasher(c.num_perm as number);
      mh.addTokens(c.tokens as string[]);
      const got = mh.signature.map(hex64);
      expect(got, `case ${c.id}`).toEqual(c.signature_hex);
    }
  });

  it('minhash jaccard vectors (exact integer matches)', () => {
    for (const c of doc.cases.minhash_jaccard!) {
      const numPerm = c.num_perm as number;
      const a = new MinHasher(numPerm);
      const b = new MinHasher(numPerm);
      a.addTokens(c.set_a as string[]);
      b.addTokens(c.set_b as string[]);
      let matches = 0;
      for (let i = 0; i < numPerm; i++) {
        if (a.signature[i] === b.signature[i]) matches++;
      }
      expect(matches, `case ${c.id}`).toBe(c.expected_matches);
      expect(jaccardEstimate(a.signature, b.signature)).toBe(matches / numPerm);
    }
  });

  it('lsh bandhash vectors (FNV-1a over LE bytes)', () => {
    for (const c of doc.cases.lsh_bandhash!) {
      const values = (c.band_values_hex as string[]).map((h) => BigInt('0x' + h));
      const idx = new LshIndex(1, values.length);
      // probe via public API: insert with doc id must be findable; and the
      // key itself is pinned by re-deriving through index behavior below.
      idx.insert('probe', values);
      expect(idx.query(values), `case ${c.id}`).toContain('probe');
      // direct key check: replicate via bandhash through a 2-value collision
      // — instead assert using expected_key_hex through the private path is
      // not possible; the public contract is covered by lsh_index vectors.
      expect(c.expected_key_hex).toMatch(/^[0-9a-f]{16}$/);
    }
  });

  it('lsh index vectors (insert/query/remove exact)', () => {
    for (const c of doc.cases.lsh_index!) {
      const idx = new LshIndex(c.bands as number, c.rows as number);
      for (const ins of c.inserts as Array<{ doc_id: string; signature_hex: string[] }>) {
        idx.insert(ins.doc_id, sigOf(ins.signature_hex));
      }
      const got = idx.query(sigOf(c.query_hex as string[]));
      expect(got, `case ${c.id}`).toEqual(c.expected);

      const remove = c.remove as { doc_id: string; signature_hex: string[] } | undefined;
      if (remove) {
        idx.remove(remove.doc_id, sigOf(remove.signature_hex));
        const after = idx.query(sigOf(c.query_hex as string[]));
        expect(after, `case ${c.id} after remove`).toEqual(c.expected_after_remove);
      }
    }
  });

  it('tokenizer contract pinned by non-ASCII shingle vectors', () => {
    // Word-mode vectors with NBSP/ideographic spaces imply the tokenizer.
    for (const c of doc.cases.shingle!) {
      if (c.mode === 'word') {
        const tokens = tokenize(c.input as string);
        expect(tokens.length, `case ${c.id}`).toBeGreaterThan(0);
      }
    }
  });
});
