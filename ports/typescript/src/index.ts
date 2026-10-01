/**
 * LombokSimHash — TypeScript Port
 * Near-duplicate document detection for RAG pipelines.
 * Zero dependencies, pure TypeScript with BigInt for 64-bit math.
 *
 * @module lomboksimhash
 * @license Apache-2.0
 */

// ============================================================
// SHA-256 (FIPS 180-4)
// ============================================================

const K_SHA: number[] = [
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
    w[i] = ((block[i*4] << 24) | (block[i*4+1] << 16) |
             (block[i*4+2] << 8) | block[i*4+3]) >>> 0;
  }
  for (let i = 16; i < 64; i++) {
    const s0 = rotr32(w[i-15], 7) ^ rotr32(w[i-15], 18) ^ (w[i-15] >>> 3);
    const s1 = rotr32(w[i-2], 17) ^ rotr32(w[i-2], 19) ^ (w[i-2] >>> 10);
    w[i] = (w[i-16] + s0 + w[i-7] + s1) >>> 0;
  }

  let [a, b, c, d, e, f, g, h] = state;

  for (let i = 0; i < 64; i++) {
    const s1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
    const ch = (e & f) ^ (~e & g);
    const temp1 = (h + s1 + (ch >>> 0) + K_SHA[i] + w[i]) >>> 0;
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

function textToBytes(text: string): Uint8Array {
  return new TextEncoder().encode(text);
}

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

  return state.map(v => v.toString(16).padStart(8, '0')).join('');
}

// ============================================================
// FNV-1a 64-bit
// ============================================================

const FNV64_OFFSET = 0xcbf29ce484222325n;
const FNV64_PRIME = 0x100000001b3n;
const MASK64 = (1n << 64n) - 1n;

export function fnv1a64(data: Uint8Array): bigint {
  let h = FNV64_OFFSET;
  for (const b of data) {
    h ^= BigInt(b);
    h = (h * FNV64_PRIME) & MASK64;
  }
  return h;
}

// ============================================================
// Shingling
// ============================================================

export type ShingleMode = 'character' | 'word';

export class Shingler {
  private buffer = '';
  constructor(public readonly mode: ShingleMode, public readonly n: number) {
    if (n < 1) throw new Error('shingle size must be > 0');
  }

  feed(text: string): void {
    this.buffer += text;
  }

  finish(): string[] {
    const set = new Set<string>();
    if (this.mode === 'character') {
      const chars = [...this.buffer];
      for (let i = 0; i <= chars.length - this.n; i++) {
        set.add(chars.slice(i, i + this.n).join(''));
      }
    } else {
      const words = this.buffer.split(/\s+/).filter(w => w.length > 0);
      for (let i = 0; i <= words.length - this.n; i++) {
        set.add(words.slice(i, i + this.n).join(' '));
      }
    }
    return [...set].sort();
  }
}

// ============================================================
// SimHash
// ============================================================

export function simhash64(tokens: string[]): bigint {
  const v = new Array<number>(64).fill(0);
  for (const token of tokens) {
    const h = fnv1a64(textToBytes(token));
    for (let i = 0; i < 64; i++) {
      if ((h >> BigInt(i)) & 1n) {
        v[i]++;
      } else {
        v[i]--;
      }
    }
  }
  let result = 0n;
  for (let i = 0; i < 64; i++) {
    if (v[i] > 0) result |= 1n << BigInt(i);
  }
  return result;
}

export function simhash64Text(text: string): bigint {
  return simhash64(text.split(/\s+/).filter(w => w.length > 0));
}

export function hamming64(a: bigint, b: bigint): number {
  let xor = (a ^ b) & MASK64;
  let count = 0;
  while (xor > 0n) {
    count += Number(xor & 1n);
    xor >>= 1n;
  }
  return count;
}

// ============================================================
// MinHash
// ============================================================

const MERSENNE_61 = (1n << 61n) - 1n;
const LCG_SEED = 0x517cc1b727220a95n;
const LCG_MUL = 6364136223846793005n;
const LCG_INC = 1442695040888963407n;

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

export class MinHasher {
  private params: Array<[bigint, bigint]>;
  public signature: bigint[];

  constructor(public readonly numPerm: number) {
    this.params = generateHashParams(numPerm);
    this.signature = new Array(numPerm).fill(MASK64);
  }

  add(token: string): void {
    const h = fnv1a64(textToBytes(token));
    for (let i = 0; i < this.numPerm; i++) {
      const [a, b] = this.params[i];
      const val = universalHash(a, b, h);
      if (val < this.signature[i]) {
        this.signature[i] = val;
      }
    }
  }

  addTokens(tokens: string[]): void {
    for (const t of tokens) this.add(t);
  }
}

export function jaccardEstimate(sigA: bigint[], sigB: bigint[]): number {
  if (sigA.length !== sigB.length) throw new Error('signatures must have same length');
  let matches = 0;
  for (let i = 0; i < sigA.length; i++) {
    if (sigA[i] === sigB[i]) matches++;
  }
  return matches / sigA.length;
}

// ============================================================
// LSH Index
// ============================================================

export class LshIndex {
  private buckets: Map<bigint, string[]>[];

  constructor(public readonly bands: number, public readonly rows: number) {
    this.buckets = Array.from({ length: bands }, () => new Map());
  }

  get signatureLen(): number {
    return this.bands * this.rows;
  }

  threshold(): number {
    return Math.pow(1 / this.bands, 1 / this.rows);
  }

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

  insert(docId: string, signature: bigint[]): void {
    if (signature.length !== this.signatureLen) {
      throw new Error(`signature length must be ${this.signatureLen}`);
    }
    for (let b = 0; b < this.bands; b++) {
      const start = b * this.rows;
      const bandVals = signature.slice(start, start + this.rows);
      const key = this.bandHash(bandVals);
      const bucket = this.buckets[b].get(key) || [];
      bucket.push(docId);
      this.buckets[b].set(key, bucket);
    }
  }

  query(signature: bigint[]): string[] {
    if (signature.length !== this.signatureLen) {
      throw new Error(`signature length must be ${this.signatureLen}`);
    }
    const candidates = new Set<string>();
    for (let b = 0; b < this.bands; b++) {
      const start = b * this.rows;
      const bandVals = signature.slice(start, start + this.rows);
      const key = this.bandHash(bandVals);
      const bucket = this.buckets[b].get(key);
      if (bucket) bucket.forEach(d => candidates.add(d));
    }
    return [...candidates];
  }

  remove(docId: string, signature: bigint[]): void {
    for (let b = 0; b < this.bands; b++) {
      const start = b * this.rows;
      const bandVals = signature.slice(start, start + this.rows);
      const key = this.bandHash(bandVals);
      const bucket = this.buckets[b].get(key);
      if (bucket) {
        this.buckets[b].set(key, bucket.filter(d => d !== docId));
      }
    }
  }
}
