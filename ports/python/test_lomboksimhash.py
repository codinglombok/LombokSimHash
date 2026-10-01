"""LombokSimHash Python — Test Suite"""

from lomboksimhash import (
    sha256, fnv1a64, Shingler,
    simhash64, simhash64_text, hamming64,
    MinHasher, jaccard_estimate, LshIndex,
)

passed = 0
failed = 0


def assert_eq(actual, expected, msg):
    global passed, failed
    if actual == expected:
        passed += 1
        print(f"  ✅ {msg}")
    else:
        failed += 1
        print(f"  ❌ FAIL: {msg} (got {actual}, expected {expected})")


def assert_true(condition, msg):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {msg}")
    else:
        failed += 1
        print(f"  ❌ FAIL: {msg}")


# SHA-256
print("\n=== SHA-256 ===")
assert_eq(sha256(b""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "empty")
assert_eq(sha256(b"hello"), "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", "hello")
assert_eq(sha256(b"the quick brown fox jumps over the lazy dog"),
          "05c6e08f1d9fdafa03147fcb8f82f124c76d2f70e3d989dc8aadb5e7d7450bec", "fox")
assert_eq(sha256(b"abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "abc")

# FNV-1a 64
print("\n=== FNV-1a 64 ===")
assert_eq(f"{fnv1a64(b''):x}", "cbf29ce484222325", "empty")
assert_eq(f"{fnv1a64(b'hello'):x}", "a430d84680aabd0b", "hello")

# Shingling
print("\n=== Shingling ===")
s1 = Shingler("character", 3)
s1.feed("abcde")
assert_eq(s1.finish(), ["abc", "bcd", "cde"], "char shingles 3")

s2 = Shingler("word", 2)
s2.feed("the quick brown fox")
assert_eq(s2.finish(), ["brown fox", "quick brown", "the quick"], "word shingles 2")

s3 = Shingler("character", 3)
s3.feed("abc")
s3.feed("de")
assert_eq(s3.finish(), ["abc", "bcd", "cde"], "streaming shingles")

# SimHash64
print("\n=== SimHash64 ===")
fox = simhash64_text("the quick brown fox jumps over the lazy dog")
assert_eq(f"{fox:016x}", "cab7991c5475edee", "fox simhash")

cat = simhash64_text("the quick brown cat jumps over the lazy dog")
assert_eq(f"{cat:016x}", "c2e7991c1465e56f", "cat simhash")

assert_eq(hamming64(fox, cat), 8, "fox-cat hamming = 8")
assert_eq(hamming64(fox, fox), 0, "identical hamming = 0")

# Determinism
print("\n=== Determinism ===")
h1 = simhash64_text("test determinism")
h2 = simhash64_text("test determinism")
assert_eq(h1, h2, "deterministic simhash")

# MinHash
print("\n=== MinHash ===")
a = MinHasher(128)
b = MinHasher(128)
a.add_tokens(["the", "quick", "brown", "fox"])
b.add_tokens(["the", "quick", "brown", "fox"])
assert_eq(jaccard_estimate(a.signature, b.signature), 1.0, "identical sets J=1.0")

c = MinHasher(128)
d = MinHasher(128)
c.add_tokens(["alpha", "beta", "gamma"])
d.add_tokens(["delta", "epsilon", "zeta"])
j_dis = jaccard_estimate(c.signature, d.signature)
assert_true(j_dis < 0.2, f"disjoint sets J < 0.2 (got {j_dis:.3f})")

e = MinHasher(128)
f = MinHasher(128)
e.add_tokens(["a", "b", "c", "d"])
f.add_tokens(["c", "d", "e", "f"])
j_ov = jaccard_estimate(e.signature, f.signature)
assert_true(0.1 < j_ov < 0.6, f"overlapping J ≈ 0.33 (got {j_ov:.3f})")

# MinHash determinism
g = MinHasher(64)
h = MinHasher(64)
g.add_tokens(["hello", "world"])
h.add_tokens(["hello", "world"])
assert_eq(g.signature, h.signature, "deterministic minhash")

# LSH
print("\n=== LSH ===")
lsh = LshIndex(20, 5)
assert_true(abs(lsh.threshold() - 0.5493) < 0.01, f"threshold ≈ 0.5493 (got {lsh.threshold():.4f})")

mh_doc = MinHasher(100)
mh_doc.add_tokens(["the", "quick", "brown", "fox"])
lsh.insert("doc1", mh_doc.signature)
cands = lsh.query(mh_doc.signature)
assert_true("doc1" in cands, "LSH query finds identical")

lsh.remove("doc1", mh_doc.signature)
cands2 = lsh.query(mh_doc.signature)
assert_true("doc1" not in cands2, "LSH remove works")

# Summary
print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print(f"{'='*40}")
if failed > 0:
    exit(1)
