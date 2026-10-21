import { describe, expect, it } from 'vitest';

import {
  ERR,
  LshIndex,
  MinHasher,
  Shingler,
  charShingles,
  compareCodePoints,
  fnv1a64,
  hamming128,
  hamming64,
  jaccardEstimate,
  sha256,
  simhash128,
  simhash128Text,
  simhash64,
  simhash64Text,
  textToBytes,
  tokenize,
  wordShingles,
} from './index.js';

describe('sha256', () => {
  it('matches FIPS 180-4 reference digests', () => {
    expect(sha256('')).toBe(
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    );
    expect(sha256('abc')).toBe(
      'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    );
  });

  it('accepts raw bytes and text identically (UTF-8)', () => {
    expect(sha256(textToBytes('héllo'))).toBe(sha256('héllo'));
    expect(sha256(new Uint8Array([0, 1, 2, 255]))).toBe(
      sha256(new Uint8Array([0, 1, 2, 255]))
    );
  });
});

describe('fnv1a64', () => {
  it('has the spec offset for empty input', () => {
    expect(fnv1a64(new Uint8Array(0))).toBe(0xcbf29ce484222325n);
  });

  it('matches known values', () => {
    expect(fnv1a64(textToBytes('hello')).toString(16)).toBe('a430d84680aabd0b');
  });
});

describe('tokenize (SPEC whitespace)', () => {
  it('splits on runs of the 25 White_Space code points', () => {
    expect(tokenize('a\u00a0b\u3000c\u000bd')).toEqual(['a', 'b', 'c', 'd']);
  });

  it('does NOT split on U+200B or U+FEFF (not in contract)', () => {
    expect(tokenize('a\u200bb')).toEqual(['a\u200bb']);
    expect(tokenize('a\ufeffb')).toEqual(['a\ufeffb']);
  });

  it('returns [] for empty and whitespace-only text', () => {
    expect(tokenize('')).toEqual([]);
    expect(tokenize(' \t\n\u00a0')).toEqual([]);
  });
});

describe('compareCodePoints', () => {
  it('orders supplementary plane after BMP high range (UTF-8 byte order)', () => {
    expect(compareCodePoints('\uffff', '\u{10000}')).toBe(-1);
    expect(compareCodePoints('\u{10000}', '\uffff')).toBe(1);
    expect(compareCodePoints('abc', 'abc')).toBe(0);
  });
});

describe('shingling', () => {
  it('character mode slices code points and sorts them', () => {
    expect(charShingles('abcde', 3)).toEqual(['abc', 'bcd', 'cde']);
  });

  it('word mode uses the SPEC tokenizer and single-space joins', () => {
    expect(wordShingles('a   b\t\tc\n\nc', 2)).toEqual(['a b', 'b c', 'c c']);
  });

  it('empty result when n exceeds length', () => {
    expect(charShingles('ab', 5)).toEqual([]);
    expect(wordShingles('a b', 4)).toEqual([]);
  });

  it('rejects n < 1 with [ERR_SHINGLE_N]', () => {
    expect(() => new Shingler('character', 0)).toThrowError(ERR.SHINGLE_N);
    expect(() => charShingles('abc', 0)).toThrowError(ERR.SHINGLE_N);
    expect(() => wordShingles('abc', -2)).toThrowError(ERR.SHINGLE_N);
  });

  it('rejects invalid mode', () => {
    expect(() => new Shingler('bogus' as never, 2)).toThrowError(/mode/);
  });

  it('streaming equals one-shot', () => {
    const s = new Shingler('character', 3);
    s.feed('abc');
    s.feed('de');
    expect(s.finish()).toEqual(charShingles('abcde', 3));
    expect(s.finish()).toEqual(charShingles('abcde', 3)); // finish is pure
  });
});

describe('simhash64', () => {
  it('matches known fingerprints', () => {
    expect(simhash64Text('the quick brown fox jumps over the lazy dog').toString(16))
      .toBe('cab7991c5475edee');
    expect(simhash64Text('the quick brown cat jumps over the lazy dog').toString(16))
      .toBe('c2e7991c1465e56f');
  });

  it('empty token list yields 0', () => {
    expect(simhash64([]).toString(16)).toBe('0');
    expect(simhash64Text('   \t\n').toString(16)).toBe('0');
  });

  it('is deterministic', () => {
    expect(simhash64Text('test determinism')).toBe(simhash64Text('test determinism'));
  });

  it('hamming64 counts differing bits', () => {
    const fox = simhash64Text('the quick brown fox jumps over the lazy dog');
    const cat = simhash64Text('the quick brown cat jumps over the lazy dog');
    expect(hamming64(fox, cat)).toBe(8);
    expect(hamming64(fox, fox)).toBe(0);
  });
});

describe('simhash128', () => {
  it('lo word equals simhash64 of the same tokens', () => {
    const text = 'the quick brown fox jumps over the lazy dog';
    const [, lo] = simhash128Text(text);
    expect(lo).toBe(simhash64Text(text));
  });

  it('hamming128 sums hi and lo popcounts', () => {
    const a = simhash128Text('hello world');
    const b = simhash128Text('hello wörld');
    expect(hamming128(a, a)).toBe(0);
    expect(hamming128(a, b)).toBe(hamming64(a[0], b[0]) + hamming64(a[1], b[1]));
  });

  it('empty token list yields (0, 0)', () => {
    expect(simhash128([])).toEqual([0n, 0n]);
  });
});

describe('minhash', () => {
  it('identical sets give Jaccard 1.0', () => {
    const a = new MinHasher(128);
    const b = new MinHasher(128);
    a.addTokens(['the', 'quick', 'brown', 'fox']);
    b.addTokens(['the', 'quick', 'brown', 'fox']);
    expect(jaccardEstimate(a.signature, b.signature)).toBe(1.0);
  });

  it('is deterministic and token order independent', () => {
    const a = new MinHasher(64);
    const b = new MinHasher(64);
    a.addTokens(['hello', 'world']);
    b.addTokens(['world', 'hello']);
    expect(a.signature).toEqual(b.signature);
  });

  it('duplicate tokens are idempotent', () => {
    const a = new MinHasher(32);
    const b = new MinHasher(32);
    a.addTokens(['a', 'a', 'b']);
    b.addTokens(['a', 'b']);
    expect(a.signature).toEqual(b.signature);
  });

  it('rejects num_perm < 1 with [ERR_MINHASH_PERM]', () => {
    expect(() => new MinHasher(0)).toThrowError(ERR.MINHASH_PERM);
  });

  it('rejects jaccard errors', () => {
    const a = new MinHasher(8);
    const b = new MinHasher(16);
    expect(() => jaccardEstimate(a.signature, b.signature)).toThrowError(ERR.JACCARD_LEN);
    expect(() => jaccardEstimate([], [])).toThrowError(ERR.JACCARD_EMPTY);
  });
});

describe('lsh', () => {
  it('rejects bad config with [ERR_LSH_CONFIG]', () => {
    expect(() => new LshIndex(0, 5)).toThrowError(ERR.LSH_CONFIG);
    expect(() => new LshIndex(20, 0)).toThrowError(ERR.LSH_CONFIG);
  });

  it('rejects wrong signature length with [ERR_SIG_LEN]', () => {
    const idx = new LshIndex(5, 2);
    expect(() => idx.insert('d', [1n, 2n, 3n])).toThrowError(ERR.SIG_LEN(10));
    expect(() => idx.query([1n])).toThrowError(ERR.SIG_LEN(10));
  });

  it('query returns sorted unique candidates', () => {
    const idx = new LshIndex(3, 1);
    const sig = [1n, 2n, 3n];
    idx.insert('b_doc', sig);
    idx.insert('a_doc', sig);
    idx.insert('c_doc', sig);
    idx.insert('a_doc', sig); // duplicate id
    expect(idx.query(sig)).toEqual(['a_doc', 'b_doc', 'c_doc']);
  });

  it('remove drops the doc from touched buckets', () => {
    const idx = new LshIndex(20, 5);
    const mh = new MinHasher(100);
    mh.addTokens(['hello', 'world']);
    idx.insert('doc1', mh.signature);
    expect(idx.query(mh.signature)).toContain('doc1');
    idx.remove('doc1', mh.signature);
    expect(idx.query(mh.signature)).not.toContain('doc1');
  });

  it('threshold approximates (1/bands)^(1/rows)', () => {
    expect(Math.abs(new LshIndex(20, 5).threshold() - 0.5493)).toBeLessThan(0.01);
    expect(new LshIndex(1, 1).threshold()).toBe(1);
  });
});
