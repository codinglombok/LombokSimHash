# LombokSimHash

> Near-duplicate document detection for RAG pipelines — SimHash, MinHash, LSH, SHA-256, and shingling.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/codinglombok/LombokSimHash/actions/workflows/ci.yml/badge.svg)](https://github.com/codinglombok/LombokSimHash/actions/workflows/ci.yml)

**LombokSimHash** is library #02 of [LombokRAGFrameworks](https://github.com/codinglombok/LombokRAGFrameworks) —
a Tier 4 Hub in the Lombok Ecosystem. It identifies redundant documents *before* they
enter your vector store, preventing wasteful indexing of duplicate content.

- **Zero runtime dependencies** — pure implementation in every language (dev-only test tooling allowed)
- **no_std compatible** — Rust core runs in embedded/WASM environments (`core` + `alloc` only)
- **Deterministic across languages** — bit-identical hash values in Rust, TypeScript, Python, Go, and PHP,
  verified against one shared vector file (`vectors/lomboksimhash-vectors-v2.json`)
- **Streaming API** — process large documents chunk-by-chunk (`Sha256State`, `Shingler`)
- **Fail-closed errors** — uniform `[KODE] pesan` error contract across all ports

## Installation

| Language | Command |
|----------|---------|
| Rust | `cargo add lomboksimhash` |
| TypeScript | `npm install lomboksimhash` (primary npm publication of the ecosystem) |
| Python | `pip install lomboksimhash` |
| Go | `go get github.com/codinglombok/LombokSimHash/ports/go` |
| PHP | `composer require codinglombok/lomboksimhash` |

## What's inside

| Feature | Purpose |
|---------|---------|
| **SimHash** (64/128-bit) | Fast fingerprinting; Hamming distance for near-duplicate detection |
| **MinHash** | Jaccard similarity estimation via k-permutation hashing |
| **LSH** | Band+row locality-sensitive hashing for approximate nearest neighbors |
| **SHA-256** | Exact content deduplication (FIPS 180-4) |
| **Shingling** | Character / word n-gram generation with streaming support |

## Quick Start

### Rust

```rust
use lomboksimhash::{simhash64_text, hamming64};

let a = simhash64_text("the quick brown fox jumps over the lazy dog");
let b = simhash64_text("the quick brown cat jumps over the lazy dog");

let distance = hamming64(a, b);   // 8
let similar = distance <= 3;      // false — different enough
```

### TypeScript

```typescript
import { simhash64Text, hamming64, MinHasher, jaccardEstimate, LshIndex } from 'lomboksimhash';

const a = simhash64Text('the quick brown fox jumps over the lazy dog');
const b = simhash64Text('the quick brown cat jumps over the lazy dog');
console.log(hamming64(a, b));  // 8

// MinHash + Jaccard
const mh1 = new MinHasher(128);
mh1.addTokens(['the', 'quick', 'brown', 'fox']);
const mh2 = new MinHasher(128);
mh2.addTokens(['the', 'quick', 'brown', 'fox']);
console.log(jaccardEstimate(mh1.signature, mh2.signature));  // 1.0
```

### Python

```python
from lomboksimhash import simhash64_text, hamming64, MinHasher, jaccard_estimate, LshIndex

a = simhash64_text("the quick brown fox jumps over the lazy dog")
b = simhash64_text("the quick brown cat jumps over the lazy dog")
print(hamming64(a, b))  # 8

# LSH index for approximate nearest neighbors
lsh = LshIndex(bands=20, rows=5)          # threshold ≈ 0.549
mh = MinHasher(num_perm=100)              # 20 * 5 = 100
mh.add_tokens(["the", "quick", "brown", "fox"])
lsh.insert("doc1", mh.signature)
print(lsh.query(mh.signature))            # ['doc1']
```

### Go

```go
import "github.com/codinglombok/LombokSimHash/ports/go"

a := lomboksimhash.SimHash64Text("the quick brown fox jumps over the lazy dog")
b := lomboksimhash.SimHash64Text("the quick brown cat jumps over the lazy dog")
dist := lomboksimhash.Hamming64(a, b)  // 8
```

### PHP

```php
use CodingLombok\LombokSimHash\LombokSimHash;

$a = LombokSimHash::simhash64Text('the quick brown fox jumps over the lazy dog');
$b = LombokSimHash::simhash64Text('the quick brown cat jumps over the lazy dog');
echo LombokSimHash::hamming64($a, $b);  // 8
```

## CLI (Rust)

```bash
$ lomboksimhash-cli simhash "hello world"
$ lomboksimhash-cli sha256 "hello world"
$ lomboksimhash-cli compare "text one" "text two"
Text 1 SimHash: ...
Text 2 SimHash: ...
Hamming distance: 12
Similarity: 81.3%
```

## Deduplication in a RAG pipeline

```
Document ──┬─→ SHA-256 ──────────→ exact duplicate?   → skip
           ├─→ SimHash64 ─────────→ Hamming ≤ 3?       → near-duplicate, skip
           └─→ Shingle → MinHash → LSH candidate + Jaccard ≥ 0.8? → skip
                                              ↓
                                        otherwise → chunk + embed
```

## Configuration

| Parameter | Default | Notes |
|-----------|---------|-------|
| SimHash bits | 64 | 128-bit variant available for lower collision |
| Shingle size | configurable | character or word n-grams |
| MinHash permutations | 128 | more permutations = better Jaccard estimate |
| LSH bands × rows | 20 × 5 | `bands * rows` must equal signature length; threshold `(1/bands)^(1/rows)` |

## Cross-language determinism

All ports produce **bit-identical** hash values, verified against the shared,
deterministically generated vector file
[`vectors/lomboksimhash-vectors-v2.json`](vectors/lomboksimhash-vectors-v2.json)
(75 cases: SHA-256, FNV-1a, shingles, SimHash 64/128, exact MinHash signatures,
LSH band keys and index scenarios). The vectors are produced by
`vectors/generate_vectors.py` — never hand-edited; CI re-verifies determinism.

Guaranteed by fixed constants: FNV-1a (`0xcbf29ce484222325` / `0x100000001b3`),
LCG seed `0x517cc1b727220a95`, and Mersenne prime `2^61 - 1`.

| Input | SHA-256 | SimHash64 |
|-------|---------|-----------|
| `"the quick brown fox jumps over the lazy dog"` | `05c6e08f…7450bec` | `cab7991c5475edee` |
| `"the quick brown cat jumps over the lazy dog"` | — | `c2e7991c1465e56f` |

## Error contract

All ports fail closed with identical byte-for-byte messages:

| Kode | Pesan |
|------|-------|
| `[ERR_SHINGLE_N]` | shingle size must be > 0 |
| `[ERR_MINHASH_PERM]` | num_perm must be > 0 |
| `[ERR_LSH_CONFIG]` | bands and rows must be > 0 |
| `[ERR_SIG_LEN]` | signature length must be bands * rows = {n} |
| `[ERR_JACCARD_LEN]` | signatures must have same length |
| `[ERR_JACCARD_EMPTY]` | signatures must not be empty |

## Documentation

- [Changelog](changelog.md) — version history
- [TypeScript port](ports/typescript/README.md) · [Python port](ports/python/README.md) · [Go port](ports/go/README.md) · [PHP port](ports/php/README.md)
- Internal design docs (SPEC, Architecture, Masterplan, …) live in `docs/` per the
  Lombok Ecosystem documentation pack.

## License

[Apache 2.0](LICENSE) © CodingLombok
