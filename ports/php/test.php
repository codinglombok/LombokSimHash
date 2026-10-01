<?php
/**
 * LombokSimHash PHP — Test Suite
 */

require_once __DIR__ . '/src/LombokSimHash.php';

use CodingLombok\LombokSimHash\LombokSimHash;

$passed = 0;
$failed = 0;

function assert_eq($actual, $expected, string $msg): void {
    global $passed, $failed;
    if ($actual === $expected) {
        $passed++;
        echo "  ✅ $msg\n";
    } else {
        $failed++;
        echo "  ❌ FAIL: $msg (got " . var_export($actual, true) . ", expected " . var_export($expected, true) . ")\n";
    }
}

function assert_true(bool $condition, string $msg): void {
    global $passed, $failed;
    if ($condition) {
        $passed++;
        echo "  ✅ $msg\n";
    } else {
        $failed++;
        echo "  ❌ FAIL: $msg\n";
    }
}

// SHA-256
echo "\n=== SHA-256 ===\n";
assert_eq(LombokSimHash::sha256(''), 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'empty');
assert_eq(LombokSimHash::sha256('hello'), '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824', 'hello');
assert_eq(LombokSimHash::sha256('abc'), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad', 'abc');

// FNV-1a 64
echo "\n=== FNV-1a 64 ===\n";
assert_eq(gmp_strval(LombokSimHash::fnv1a64(''), 16), 'cbf29ce484222325', 'empty');
assert_eq(gmp_strval(LombokSimHash::fnv1a64('hello'), 16), 'a430d84680aabd0b', 'hello');

// Shingling
echo "\n=== Shingling ===\n";
assert_eq(LombokSimHash::charShingles('abcde', 3), ['abc', 'bcd', 'cde'], 'char shingles 3');
assert_eq(LombokSimHash::wordShingles('the quick brown fox', 2), ['brown fox', 'quick brown', 'the quick'], 'word shingles 2');

// SimHash64
echo "\n=== SimHash64 ===\n";
$fox = LombokSimHash::simhash64Text('the quick brown fox jumps over the lazy dog');
assert_eq(str_pad(gmp_strval($fox, 16), 16, '0', STR_PAD_LEFT), 'cab7991c5475edee', 'fox simhash');

$cat = LombokSimHash::simhash64Text('the quick brown cat jumps over the lazy dog');
assert_eq(str_pad(gmp_strval($cat, 16), 16, '0', STR_PAD_LEFT), 'c2e7991c1465e56f', 'cat simhash');

assert_eq(LombokSimHash::hamming64($fox, $cat), 8, 'fox-cat hamming = 8');
assert_eq(LombokSimHash::hamming64($fox, $fox), 0, 'identical hamming = 0');

// Determinism
echo "\n=== Determinism ===\n";
$h1 = LombokSimHash::simhash64Text('test determinism');
$h2 = LombokSimHash::simhash64Text('test determinism');
assert_eq(gmp_cmp($h1, $h2), 0, 'deterministic simhash');

// MinHash
echo "\n=== MinHash ===\n";
$sigA = LombokSimHash::minhash(['the', 'quick', 'brown', 'fox'], 128);
$sigB = LombokSimHash::minhash(['the', 'quick', 'brown', 'fox'], 128);
assert_eq(LombokSimHash::jaccardEstimate($sigA, $sigB), 1.0, 'identical sets J=1.0');

$sigC = LombokSimHash::minhash(['alpha', 'beta', 'gamma'], 128);
$sigD = LombokSimHash::minhash(['delta', 'epsilon', 'zeta'], 128);
$jDis = LombokSimHash::jaccardEstimate($sigC, $sigD);
assert_true($jDis < 0.2, "disjoint sets J < 0.2 (got $jDis)");

$sigE = LombokSimHash::minhash(['a', 'b', 'c', 'd'], 128);
$sigF = LombokSimHash::minhash(['c', 'd', 'e', 'f'], 128);
$jOv = LombokSimHash::jaccardEstimate($sigE, $sigF);
assert_true($jOv > 0.1 && $jOv < 0.6, sprintf("overlapping J ≈ 0.33 (got %.3f)", $jOv));

// MinHash determinism
$sigG = LombokSimHash::minhash(['hello', 'world'], 64);
$sigH = LombokSimHash::minhash(['hello', 'world'], 64);
$mhDet = true;
for ($i = 0; $i < 64; $i++) {
    if (gmp_cmp($sigG[$i], $sigH[$i]) !== 0) { $mhDet = false; break; }
}
assert_true($mhDet, 'deterministic minhash');

// LSH
echo "\n=== LSH ===\n";
$lsh = new LombokSimHash();
$lsh->initLsh(20, 5);
$th = $lsh->lshThreshold();
assert_true(abs($th - 0.5493) < 0.01, sprintf("threshold ≈ 0.5493 (got %.4f)", $th));

$mhDoc = LombokSimHash::minhash(['the', 'quick', 'brown', 'fox'], 100);
$lsh->lshInsert('doc1', $mhDoc);
$cands = $lsh->lshQuery($mhDoc);
assert_true(in_array('doc1', $cands), 'LSH query finds identical');

$lsh->lshRemove('doc1', $mhDoc);
$cands2 = $lsh->lshQuery($mhDoc);
assert_true(!in_array('doc1', $cands2), 'LSH remove works');

// Summary
echo "\n" . str_repeat('=', 40) . "\n";
echo "Results: $passed passed, $failed failed, " . ($passed + $failed) . " total\n";
echo str_repeat('=', 40) . "\n";
if ($failed > 0) exit(1);
