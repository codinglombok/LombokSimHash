"""Cross-language hash value dumper for LombokSimHash."""

from lomboksimhash import sha256, fnv1a64, simhash64_text, hamming64, MinHasher, jaccard_estimate

print("=== LombokSimHash Cross-Language Verification ===\n")

print("SHA-256:")
print(f'  ""      => {sha256(b"")}')
print(f'  "hello" => {sha256(b"hello")}')
print(f'  "abc"   => {sha256(b"abc")}')

print("\nFNV-1a 64:")
print(f'  ""      => {fnv1a64(b""):x}')
print(f'  "hello" => {fnv1a64(b"hello"):x}')
print(f'  "the"   => {fnv1a64(b"the"):x}')

print("\nSimHash64:")
fox = simhash64_text("the quick brown fox jumps over the lazy dog")
cat = simhash64_text("the quick brown cat jumps over the lazy dog")
print(f"  fox => {fox:016x}")
print(f"  cat => {cat:016x}")
print(f"  hamming(fox, cat) => {hamming64(fox, cat)}")

print("\nMinHash (128 perm, identical sets):")
a = MinHasher(128)
b = MinHasher(128)
a.add_tokens(["the", "quick", "brown", "fox"])
b.add_tokens(["the", "quick", "brown", "fox"])
print(f"  Jaccard => {jaccard_estimate(a.signature, b.signature)}")
print(f"  sig[0]  => {a.signature[0]:x}")
print(f"  sig[1]  => {a.signature[1]:x}")
print(f"  sig[2]  => {a.signature[2]:x}")
