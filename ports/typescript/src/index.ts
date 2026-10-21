/**
 * LombokSimHash — TypeScript Port
 * Near-duplicate document detection for RAG pipelines.
 * Zero runtime dependencies, pure TypeScript with BigInt for 64-bit math.
 *
 * Behavior is pinned by docs/SPEC_LombokSimHash_0.1.0.md; all ports are
 * validated against vectors/lomboksimhash-vectors-v2.json (bit-identical).
 *
 * Part of LombokRAGFrameworks (Lombok Ecosystem).
 * @license Apache-2.0
 */

// ============================================================
// Errors — cross-language [KODE] messages (byte-identical)
// ============================================================

export const ERR = {
  SHINGLE_N: '[ERR_SHINGLE_N] shingle size must be > 0',
  MINHASH_PERM: '[ERR_MINHASH_PERM] num_perm must be > 0',
  LSH_CONFIG: '[ERR_LSH_CONFIG] bands and rows must be > 0',
  SIG_LEN: (n: number): string =>
    `[ERR_SIG_LEN] signature length must be bands * rows = ${n}`,
  JACCARD_LEN: '[ERR_JACCARD_LEN] signatures must have same length',
  JACCARD_EMPTY: '[ERR_JACCARD_EMPTY] signatures must not be empty',
} as const;

// ============================================================
// SHA-256 (FIPS 180-4)
// ============================================================

const K_SHA: readonly number[] = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
  0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
  0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

const H_INIT = [
  0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
  0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
];

function rotr32(x: number, n: number): number {
  return ((x >>> n) | (x << (32 - n))) >>> 0;
}

function sha256Compress(state: number[], block: Uint8Array): void {
  const w = new Array<number>(64);
  for (let i = 0; i < 16; i++) {
    w[i] = ((block[i * 4]! << 24) | (block[i * 4 + 1]! << 16) |
            (block[i * 4 + 2]! << 8) | block[i * 4 + 3]!) >>> 0;
  }
  for (let i = 16; i < 64; i++) {
    const wm15 = w[i - 15]!;
    const wm2 = w[i - 2]!;
    const s0 = rotr32(wm15, 7) ^ rotr32(wm15, 18) ^ (wm15 >>> 3);
    const s1 = rotr32(wm2, 17) ^ rotr32(wm2, 19) ^ (wm2 >>> 10);
    w[i] = (w[i - 16]! + s0 + w[i - 7]! + s1) >>> 0;
  }

  let [a, b, c, d, e, f, g, h] = state;

  for (let i = 0; i < 64; i++) {
    const s1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
    const ch = (e & f) ^ (~e & g);
    const temp1 = (h + s1 + (ch >>> 0) + K_SHA[i]! + w[i]!) >>> 0;
    const s0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
    const maj = (a & b) ^ (a & c) ^ (b & c);
    const temp2 = (s0 + maj) >>> 0;

    h = g; g = f; f = e;
    e = (d + temp1) >>> 0;
    d = c; c = b; b = a;
    a = (temp1 + temp2) >>> 0;
  }

  state[0] = (state[0] + a) >>> 0;
  state[1] = (state[1] + b) >>> 0;
  state[2] = (state[2] + c) >>> 0;
  state[3] = (state[3] + d) >>> 0;
  state[4] = (state[4] + e) >>> 0;
  state[5] = (state[5] + f) >>> 0;
  state[6] = (state[6] + g) >>> 0;
  state[7] = (state[7] + h) >>> 0;
}

export function textToBytes(text: string): Uint8Array {
  return new TextEncoder().encode(text);
}

/**
 * Compute SHA-256 of bytes or UTF-8 text. Returns 64 lowercase hex chars.
 */
export function sha256(input: string | Uint8Array): string {
  const data = typeof input === 'string' ? textToBytes(input) : input;
  const state = [...H_INIT];

  const bitLen = BigInt(data.length) * 8n;
  const padded: number[] = [...data, 0x80];
  while (padded.length % 64 !== 56) padded.push(0);
  const bitBytes = new Uint8Array(8);
  for (let i = 0; i < 8; i++) {
    bitBytes[7 - i] = Number((bitLen >> BigInt(i * 8)) & 0xFFn);
  }
  padded.push(...bitBytes);

  for (let i = 0; i < padded.length; i += 64) {
    sha256Compress(state, new Uint8Array(padded.slice(i, i + 64)));
  }

  return state.map((v) => v.toString(16).padStart(8, '0')).join('');
}

// ============================================================
// FNV-1a 64-bit
// ============================================================

export const FNV64_OFFSET = 0xcbf29ce484222325n;
export const FNV64_PRIME = 0x100000001b3n;
export const MASK64 = (1n << 64n) - 1n;

/**
 * FNV-1a 64-bit hash (offset 0xcbf29ce484222325, prime 0x100000001b3).
 */
export function fnv1a64(data: Uint8Array): bigint {
  let h = FNV64_OFFSET;
  for (const b of data) {
    h ^= BigInt(b);
    h = (h * FNV64_PRIME) & MASK64;
  }
  return h;
}

/**
 * Format a u64 as 16 lowercase hex chars.
 */
export function toHex64(value: bigint): string {
  return value.toString(16).padStart(16, '0');
}

// ============================================================
// Tokenization — exact SPEC whitespace contract
// ============================================================

/**
 * The SPEC whitespace set = Unicode White_Space property (25 code points).
 * Pinned explicitly because language built-ins differ (e.g. JS `\s` also
 * matches U+FEFF, Python splits on U+001C..U+001F).
 */
export const SPEC_WHITESPACE: ReadonlySet<number> = new Set([
  0x0009, 0x000A, 0x000B, 0x000C, 0x000D, 0x0020, 0x0085, 0x00A0, 0x1680,
  0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008,
  0x2009, 0x200A, 0x2028, 0x2029, 0x202F, 0x205F, 0x3000,
]);

/**
 * Split text on runs of SPEC whitespace; drop empty parts.
 */
export function tokenize(text: string): string[] {
  const parts: string[] = [];
  let cur: string[] = [];
  for (const ch of text) {
    if (SPEC_WHITESPACE.has(ch.codePointAt(0)!)) {
      if (cur.length > 0) {
        parts.push(cur.join(''));
        cur = [];
      }
    } else {
      cur.push(ch);
    }
  }
  if (cur.length > 0) parts.push(cur.join(''));
  return parts;
}

/**
 * Compare two strings by Unicode code points (byte order of UTF-8).
 */
export function compareCodePoints(a: string, b: string): number {
  const ap = [...a];
  const bp = [...b];
  const len = Math.min(ap.length, bp.length);
  for (let i = 0; i < len; i++) {
    const ca = ap[i]!.codePointAt(0)!;
    const cb = bp[i]!.codePointAt(0)!;
    if (ca !== cb) return ca < cb ? -1 : 1;
  }
  if (ap.length === bp.length) return 0;
  return ap.length < bp.length ? -1 : 1;
}

function sortCodePoints(values: string[]): string[] {
  return [...values].sort(compareCodePoints);
}

// ============================================================
// Shingling
// ============================================================

export type ShingleMode = 'character' | 'word';

/**
 * Streaming shingle generator.
 * Character mode slices Unicode code points; word mode uses tokenize()
 * and joins with a single space. finish() sorts by code point.
 */
export class Shingler {
  public readonly mode: ShingleMode;
  public readonly n: number;
  private buffer = '';

  constructor(mode: ShingleMode, n: number) {
    if (!Number.isInteger(n) || n < 1) throw new Error(ERR.SHINGLE_N);
    if (mode !== 'character' && mode !== 'word') {
      throw new Error("mode must be 'character' or 'word'");
    }
    this.mode = mode;
    this.n = n;
  }

  feed(text: string): void {
    this.buffer += text;
  }

  finish(): string[] {
    const set = new Set<string>();
    if (this.mode === 'character') {
      const chars = [...this.buffer];
      for (let i = 0; i + this.n <= chars.length; i++) {
        set.add(chars.slice(i, i + this.n).join(''));
      }
    } else {
      const words = tokenize(this.buffer);
      for (let i = 0; i + this.n <= words.length; i++) {
        set.add(words.slice(i, i + this.n).join(' '));
      }
    }
    return sortCodePoints([...set]);
  }
}

/**
 * Sorted unique character n-grams (Unicode code points).
 */
export function charShingles(text: string, n: number): string[] {
  const s = new Shingler('character', n);
  s.feed(text);
  return s.finish();
}

/**
 * Sorted unique word n-grams (SPEC tokenizer).
 */
export function wordShingles(text: string, n: number): string[] {
  const s = new Shingler('word', n);
  s.feed(text);
  return s.finish();
}

// ============================================================
// SimHash
// ============================================================

/**
 * 64-bit SimHash over tokens. Bit i (LSB first) is set iff the signed
 * weight of bit i across token hashes is strictly positive.
 */
export function simhash64(tokens: string[]): bigint {
  const v = new Array<number>(64).fill(0);
  for (const token of tokens) {
    const h = fnv1a64(textToBytes(token));
    for (let i = 0; i < 64; i++) {
      if ((h >> BigInt(i)) & 1n) {
        v[i]!++;
      } else {
        v[i]!--;
      }
    }
  }
  let result = 0n;
  for (let i = 0; i < 64; i++) {
    if (v[i]! > 0) result |= 1n << BigInt(i);
  }
  return result;
}

/**
 * Tokenize by the SPEC whitespace set, then simhash64.
 */
export function simhash64Text(text: string): bigint {
  return simhash64(tokenize(text));
}

/**
 * 128-bit SimHash over tokens. Returns [hi, lo].
 * lo accumulates fnv1a64(utf8(token)); hi accumulates
 * fnv1a64(utf8(token) || 0xFF).
 */
export function simhash128(tokens: string[]): [bigint, bigint] {
  const v = new Array<number>(128).fill(0);
  for (const token of tokens) {
    const bytes = textToBytes(token);
    const withSuffix = new Uint8Array(bytes.length + 1);
    withSuffix.set(bytes, 0);
    withSuffix[bytes.length] = 0xff;
    const h1 = fnv1a64(bytes);
    const h2 = fnv1a64(withSuffix);
    for (let i = 0; i < 64; i++) {
      if ((h1 >> BigInt(i)) & 1n) {
        v[i]!++;
      } else {
        v[i]!--;
      }
      if ((h2 >> BigInt(i)) & 1n) {
        v[64 + i]!++;
      } else {
        v[64 + i]!--;
      }
    }
  }
  let lo = 0n;
  let hi = 0n;
  for (let i = 0; i < 64; i++) {
    if (v[i]! > 0) lo |= 1n << BigInt(i);
    if (v[64 + i]! > 0) hi |= 1n << BigInt(i);
  }
  return [hi, lo];
}

/**
 * Tokenize by the SPEC whitespace set, then simhash128.
 */
export function simhash128Text(text: string): [bigint, bigint] {
  return simhash128(tokenize(text));
}

/**
 * Hamming distance between two 64-bit values.
 */
export function hamming64(a: bigint, b: bigint): number {
  let xor = (a ^ b) & MASK64;
  let count = 0;
  while (xor > 0n) {
    count += Number(xor & 1n);
    xor >>= 1n;
  }
  return count;
}

/**
 * Hamming distance between two 128-bit [hi, lo] pairs.
 */
export function hamming128(a: readonly [bigint, bigint], b: readonly [bigint, bigint]): number {
  return hamming64(a[0], b[0]) + hamming64(a[1], b[1]);
}

// ============================================================
// MinHash
// ============================================================

export const MERSENNE_61 = (1n << 61n) - 1n;
export const LCG_SEED = 0x517cc1b727220a95n;
export const LCG_MUL = 6364136223846793005n;
export const LCG_INC = 1442695040888963407n;

function generateHashParams(numPerm: number): Array<[bigint, bigint]> {
  let state = LCG_SEED;
  const params: Array<[bigint, bigint]> = [];
  for (let i = 0; i < numPerm; i++) {
    state = (state * LCG_MUL + LCG_INC) & MASK64;
    let a = state % MERSENNE_61;
    if (a === 0n) a = 1n;
    state = (state * LCG_MUL + LCG_INC) & MASK64;
    const b = state % MERSENNE_61;
    params.push([a, b]);
  }
  return params;
}

function universalHash(a: bigint, b: bigint, x: bigint): bigint {
  const xMod = x % MERSENNE_61;
  return (a * xMod + b) % MERSENNE_61;
}

/**
 * MinHash signature generator with a deterministic permutation family.
 */
export class MinHasher {
  public readonly numPerm: number;
  public readonly signature: bigint[];
  private params: Array<[bigint, bigint]>;

  constructor(numPerm: number) {
    if (!Number.isInteger(numPerm) || numPerm < 1) {
      throw new Error(ERR.MINHASH_PERM);
    }
    this.numPerm = numPerm;
    this.params = generateHashParams(numPerm);
    this.signature = new Array<bigint>(numPerm).fill(MASK64);
  }

  /** Fold one token into the signature (idempotent per distinct token). */
  add(token: string): void {
    const h = fnv1a64(textToBytes(token));
    for (let i = 0; i < this.numPerm; i++) {
      const [a, b] = this.params[i]!;
      const val = universalHash(a, b, h);
      if (val < this.signature[i]!) {
        this.signature[i] = val;
      }
    }
  }

  /** Fold a sequence of tokens into the signature (order-independent). */
  addTokens(tokens: string[]): void {
    for (const t of tokens) this.add(t);
  }
}

/**
 * Estimated Jaccard = matched positions / signature length.
 */
export function jaccardEstimate(sigA: bigint[], sigB: bigint[]): number {
  if (sigA.length !== sigB.length) throw new Error(ERR.JACCARD_LEN);
  if (sigA.length === 0) throw new Error(ERR.JACCARD_EMPTY);
  let matches = 0;
  for (let i = 0; i < sigA.length; i++) {
    if (sigA[i] === sigB[i]) matches++;
  }
  return matches / sigA.length;
}

// ============================================================
// LSH Index
// ============================================================

/**
 * LSH index (band+row) over MinHash signatures.
 * query() returns de-duplicated doc IDs sorted by code point.
 */
export class LshIndex {
  public readonly bands: number;
  public readonly rows: number;
  private buckets: Map<bigint, string[]>[];

  constructor(bands: number, rows: number) {
    if (!Number.isInteger(bands) || !Number.isInteger(rows) || bands < 1 || rows < 1) {
      throw new Error(ERR.LSH_CONFIG);
    }
    this.bands = bands;
    this.rows = rows;
    this.buckets = Array.from({ length: bands }, () => new Map());
  }

  get signatureLen(): number {
    return this.bands * this.rows;
  }

  /**
   * Approximate Jaccard threshold (1/bands)^(1/rows).
   * Informational only — not part of the bit-identical contract.
   */
  threshold(): number {
    return Math.pow(1 / this.bands, 1 / this.rows);
  }

  /** FNV-1a 64 over the little-endian bytes of each band value. */
  private bandHash(bandValues: bigint[]): bigint {
    let h = FNV64_OFFSET;
    for (const val of bandValues) {
      for (let byteIdx = 0; byteIdx < 8; byteIdx++) {
        const byte = Number((val >> BigInt(byteIdx * 8)) & 0xFFn);
        h ^= BigInt(byte);
        h = (h * FNV64_PRIME) & MASK64;
      }
    }
    return h;
  }

  private assertSignatureLen(signature: bigint[]): void {
    if (signature.length !== this.signatureLen) {
      throw new Error(ERR.SIG_LEN(this.signatureLen));
    }
  }

  insert(docId: string, signature: bigint[]): void {
    this.assertSignatureLen(signature);
    for (let b = 0; b < this.bands; b++) {
      const start = b * this.rows;
      const bandVals = signature.slice(start, start + this.rows);
      const key = this.bandHash(bandVals);
      const bucket = this.buckets[b]!.get(key) ?? [];
      bucket.push(docId);
      this.buckets[b]!.set(key, bucket);
    }
  }

  query(signature: bigint[]): string[] {
    this.assertSignatureLen(signature);
    const candidates = new Set<string>();
    for (let b = 0; b < this.bands; b++) {
      const start = b * this.rows;
      const bandVals = signature.slice(start, start + this.rows);
      const key = this.bandHash(bandVals);
      const bucket = this.buckets[b]!.get(key);
      if (bucket) bucket.forEach((d) => candidates.add(d));
    }
    return sortCodePoints([...candidates]);
  }

  remove(docId: string, signature: bigint[]): void {
    this.assertSignatureLen(signature);
    for (let b = 0; b < this.bands; b++) {
      const start = b * this.rows;
      const bandVals = signature.slice(start, start + this.rows);
      const key = this.bandHash(bandVals);
      const bucket = this.buckets[b]!.get(key);
      if (bucket) {
        this.buckets[b]!.set(key, bucket.filter((d) => d !== docId));
      }
    }
  }
}
