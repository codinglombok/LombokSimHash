/**
 * Cross-language hash value dumper for LombokSimHash.
 * Run this in each language port to verify deterministic values match.
 */

import {
  sha256, fnv1a64, simhash64Text, simhash128Text, hamming64,
  MinHasher, jaccardEstimate, toHex64,
} from './index.js';

const enc = new TextEncoder();

console.log('=== LombokSimHash Cross-Language Verification ===\n');

console.log('SHA-256:');
console.log(`  ""      => ${sha256('')}`);
console.log(`  "hello" => ${sha256('hello')}`);
console.log(`  "abc"   => ${sha256('abc')}`);

console.log('\nFNV-1a 64:');
console.log(`  ""      => ${toHex64(fnv1a64(enc.encode('')))}`);
console.log(`  "hello" => ${toHex64(fnv1a64(enc.encode('hello')))}`);
console.log(`  "the"   => ${toHex64(fnv1a64(enc.encode('the')))}`);

console.log('\nSimHash64:');
const fox = simhash64Text('the quick brown fox jumps over the lazy dog');
const cat = simhash64Text('the quick brown cat jumps over the lazy dog');
console.log(`  fox => ${toHex64(fox)}`);
console.log(`  cat => ${toHex64(cat)}`);
console.log(`  hamming(fox, cat) => ${hamming64(fox, cat)}`);

console.log('\nSimHash128:');
const [foxHi, foxLo] = simhash128Text('the quick brown fox jumps over the lazy dog');
console.log(`  fox hi => ${toHex64(foxHi)}`);
console.log(`  fox lo => ${toHex64(foxLo)}`);

console.log('\nMinHash (128 perm, identical sets):');
const a = new MinHasher(128);
const b = new MinHasher(128);
a.addTokens(['the', 'quick', 'brown', 'fox']);
b.addTokens(['the', 'quick', 'brown', 'fox']);
console.log(`  Jaccard => ${jaccardEstimate(a.signature, b.signature)}`);
console.log(`  sig[0]  => ${toHex64(a.signature[0]!)}`);
console.log(`  sig[1]  => ${toHex64(a.signature[1]!)}`);
console.log(`  sig[2]  => ${toHex64(a.signature[2]!)}`);
