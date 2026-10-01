/**
 * LombokSimHash TypeScript — Test Suite
 * Tests against cross-language vectors.
 */

import {
  sha256, fnv1a64, Shingler, simhash64, simhash64Text,
  hamming64, MinHasher, jaccardEstimate, LshIndex
} from './index.js';

let pass = 0;
let fail = 0;

function assert(condition: boolean, msg: string): void {
  if (condition) {
    pass++;
    console.log(`  ✅ ${msg}`);
  } else {
    fail++;
    console.log(`  ❌ FAIL: ${msg}`);
  }
}

function assertEq<T>(actual: T, expected: T, msg: string): void {
  assert(actual === expected, `${msg} (got ${actual}, expected ${expected})`);
}

// SHA-256
console.log('\n=== SHA-256 ===');
assertEq(sha256(''), 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'empty');
assertEq(sha256('hello'), '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824', 'hello');
assertEq(sha256('the quick brown fox jumps over the lazy dog'),
  '05c6e08f1d9fdafa03147fcb8f82f124c76d2f70e3d989dc8aadb5e7d7450bec', 'fox');
assertEq(sha256('abc'), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad', 'abc');

// FNV-1a 64
console.log('\n=== FNV-1a 64 ===');
assertEq(fnv1a64(new TextEncoder().encode('')).toString(16), 'cbf29ce484222325', 'empty');
assertEq(fnv1a64(new TextEncoder().encode('hello')).toString(16), 'a430d84680aabd0b', 'hello');

// Shingling
console.log('\n=== Shingling ===');
const s1 = new Shingler('character', 3);
s1.feed('abcde');
assert(JSON.stringify(s1.finish()) === JSON.stringify(['abc', 'bcd', 'cde']), 'char shingles 3');

const s2 = new Shingler('word', 2);
s2.feed('the quick brown fox');
assert(JSON.stringify(s2.finish()) === JSON.stringify(['brown fox', 'quick brown', 'the quick']), 'word shingles 2');

const s3 = new Shingler('character', 2);
s3.feed('hello');
assert(JSON.stringify(s3.finish()) === JSON.stringify(['el', 'he', 'll', 'lo']), 'char shingles 2');

const s4 = new Shingler('character', 3);
s4.feed('abc');
s4.feed('de');
assert(JSON.stringify(s4.finish()) === JSON.stringify(['abc', 'bcd', 'cde']), 'streaming shingles');

// SimHash64
console.log('\n=== SimHash64 ===');
const foxHash = simhash64Text('the quick brown fox jumps over the lazy dog');
assertEq(foxHash.toString(16), 'cab7991c5475edee', 'fox simhash');

const catHash = simhash64Text('the quick brown cat jumps over the lazy dog');
assertEq(catHash.toString(16), 'c2e7991c1465e56f', 'cat simhash');

assertEq(hamming64(foxHash, catHash), 8, 'fox-cat hamming = 8');
assertEq(hamming64(foxHash, foxHash), 0, 'identical hamming = 0');

// SimHash determinism
console.log('\n=== SimHash Determinism ===');
const h1 = simhash64Text('test determinism');
const h2 = simhash64Text('test determinism');
assertEq(h1, h2, 'deterministic simhash');

// MinHash
console.log('\n=== MinHash ===');
const mhA = new MinHasher(128);
const mhB = new MinHasher(128);
mhA.addTokens(['the', 'quick', 'brown', 'fox']);
mhB.addTokens(['the', 'quick', 'brown', 'fox']);
assertEq(jaccardEstimate(mhA.signature, mhB.signature), 1.0, 'identical sets J=1.0');

const mhC = new MinHasher(128);
const mhD = new MinHasher(128);
mhC.addTokens(['alpha', 'beta', 'gamma']);
mhD.addTokens(['delta', 'epsilon', 'zeta']);
const jDisjoint = jaccardEstimate(mhC.signature, mhD.signature);
assert(jDisjoint < 0.2, `disjoint sets J < 0.2 (got ${jDisjoint})`);

const mhE = new MinHasher(128);
const mhF = new MinHasher(128);
mhE.addTokens(['a', 'b', 'c', 'd']);
mhF.addTokens(['c', 'd', 'e', 'f']);
const jOverlap = jaccardEstimate(mhE.signature, mhF.signature);
assert(jOverlap > 0.1 && jOverlap < 0.6, `overlapping J ≈ 0.33 (got ${jOverlap.toFixed(3)})`);

// MinHash determinism
const mhG = new MinHasher(64);
const mhH = new MinHasher(64);
mhG.addTokens(['hello', 'world']);
mhH.addTokens(['hello', 'world']);
assert(mhG.signature.every((v, i) => v === mhH.signature[i]), 'deterministic minhash');

// LSH
console.log('\n=== LSH ===');
const lsh = new LshIndex(20, 5);
assert(Math.abs(lsh.threshold() - 0.5493) < 0.01, `threshold ≈ 0.5493 (got ${lsh.threshold().toFixed(4)})`);

const mhDoc = new MinHasher(100);
mhDoc.addTokens(['the', 'quick', 'brown', 'fox']);
lsh.insert('doc1', mhDoc.signature);
const candidates = lsh.query(mhDoc.signature);
assert(candidates.includes('doc1'), 'LSH query finds identical');

lsh.remove('doc1', mhDoc.signature);
const afterRemove = lsh.query(mhDoc.signature);
assert(!afterRemove.includes('doc1'), 'LSH remove works');

// Summary
console.log(`\n========================================`);
console.log(`Results: ${pass} passed, ${fail} failed, ${pass + fail} total`);
console.log(`========================================`);
if (fail > 0) process.exit(1);
