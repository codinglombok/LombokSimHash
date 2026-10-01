/**
 * Cross-language hash value dumper for LombokSimHash.
 * Run this in each language port to verify deterministic values match.
 */

import { sha256, fnv1a64, simhash64Text, hamming64, MinHasher, jaccardEstimate } from './index.js';

const enc = new TextEncoder();

console.log('=== LombokSimHash Cross-Language Verification ===\n');

console.log('SHA-256:');
console.log(`  ""      => ${sha256('')}`);
console.log(`  "hello" => ${sha256('hello')}`);
console.log(`  "abc"   => ${sha256('abc')}`);

console.log('\nFNV-1a 64:');
console.log(`  ""      => ${fnv1a64(enc.encode('')).toString(16)}`);
console.log(`  "hello" => ${fnv1a64(enc.encode('hello')).toString(16)}`);
console.log(`  "the"   => ${fnv1a64(enc.encode('the')).toString(16)}`);

console.log('\nSimHash64:');
const fox = simhash64Text('the quick brown fox jumps over the lazy dog');
const cat = simhash64Text('the quick brown cat jumps over the lazy dog');
console.log(`  fox => ${fox.toString(16)}`);
console.log(`  cat => ${cat.toString(16)}`);
console.log(`  hamming(fox, cat) => ${hamming64(fox, cat)}`);

console.log('\nMinHash (128 perm, identical sets):');
const a = new MinHasher(128);
const b = new MinHasher(128);
a.addTokens(['the', 'quick', 'brown', 'fox']);
b.addTokens(['the', 'quick', 'brown', 'fox']);
console.log(`  Jaccard => ${jaccardEstimate(a.signature, b.signature)}`);
console.log(`  sig[0]  => ${a.signature[0].toString(16)}`);
console.log(`  sig[1]  => ${a.signature[1].toString(16)}`);
console.log(`  sig[2]  => ${a.signature[2].toString(16)}`);
