# Guide How to Use — LombokSimHash 0.1.0

Panduan pemakaian: instalasi, quickstart 5 menit, cookbook, troubleshooting.

---

## 1. Instalasi

| Bahasa | Perintah | Catatan |
|---|---|---|
| Rust | `cargo add lomboksimhash` | `no_std`: set `default-features = false` |
| TypeScript | `npm install lomboksimhash` | Node ≥ 18; dual ESM+CJS |
| Python | `pip install lomboksimhash` | Python ≥ 3.10; zero dependency |
| Go | `go get github.com/codinglombok/LombokSimHash/ports/go` | module di `ports/go` |
| PHP | `composer require codinglombok/lomboksimhash` | PHP ≥ 8.1, `ext-gmp`, `ext-mbstring` |

## 2. Quickstart 5 menit

### 2.1 Deteksi near-duplicate SimHash (kasus paling umum)

```python
from lomboksimhash import simhash64_text, hamming64

a = simhash64_text("the quick brown fox jumps over the lazy dog")
b = simhash64_text("the quick brown cat jumps over the lazy dog")

print(f"{a:016x}", f"{b:016x}")   # cab7991c5475edee c2e7991c1465e56f
print(hamming64(a, b))            # 8  (0 = identik; <=3 biasanya near-duplicate)
```

Setara di semua bahasa — hasil hex **harus identik**:

```typescript
import { simhash64Text, hamming64 } from 'lomboksimhash';
const a = simhash64Text('the quick brown fox jumps over the lazy dog');
console.log(a.toString(16).padStart(16, '0')); // cab7991c5475edee
```

```rust
use lomboksimhash::{simhash64_text, hamming64};
let a = simhash64_text("the quick brown fox jumps over the lazy dog");
assert_eq!(format!("{a:016x}"), "cab7991c5475edee");
```

### 2.2 Dedup eksak dengan SHA-256

```typescript
import { sha256 } from 'lomboksimhash';
const seen = new Set<string>();
function isExactDuplicate(doc: string): boolean {
  const d = sha256(doc);
  if (seen.has(d)) return true;
  seen.add(d);
  return false;
}
```

### 2.3 Kandidat near-duplicate dengan MinHash + LSH

```python
from lomboksimhash import MinHasher, LshIndex, jaccard_estimate

lsh = LshIndex(bands=20, rows=5)      # signature 100 elemen
mh = MinHasher(num_perm=100)          # bands * rows HARUS = num_perm
mh.add_tokens("the quick brown fox jumps over the lazy dog".split())
lsh.insert("doc-1", mh.signature)

print(lsh.query(mh.signature))        # ['doc-1']
```

## 3. Cookbook

### 3.1 Pipeline dedup RAG (3 lapis)

```python
from lomboksimhash import (sha256, simhash64_text, hamming64,
                           MinHasher, LshIndex)

class DedupPipeline:
    def __init__(self) -> None:
        self.sha_seen: set[str] = set()
        self.sim_seen: list[int] = []
        self.lsh = LshIndex(20, 5)

    def is_duplicate(self, text: str) -> bool:
        if sha256(text) in self.sha_seen:            # lapis 1: eksak
            return True
        h = simhash64_text(text)                     # lapis 2: near-dup
        if any(hamming64(h, prev) <= 3 for prev in self.sim_seen):
            return True
        mh = MinHasher(100)                          # lapis 3: kandidat LSH
        mh.add_tokens(text.split())
        for cand in self.lsh.query(mh.signature):
            pass  # bandingkan Jaccard eksak terhadap kandidat bila disimpan
        return False

    def add(self, text: str) -> None:
        self.sha_seen.add(sha256(text))
        self.sim_seen.append(simhash64_text(text))
        mh = MinHasher(100)
        mh.add_tokens(text.split())
        self.lsh.insert(f"doc{len(self.sha_seen)}", mh.signature)
```

### 3.2 Streaming dokumen besar

```rust
use lomboksimhash::{Sha256State, Shingler, ShingleMode};

let mut hasher = Sha256State::new();
let mut shingler = Shingler::new(ShingleMode::Word, 3);
for chunk in read_file_in_chunks("big.txt") {
    hasher.update(&chunk);
    shingler.feed(&chunk);
}
let digest = hasher.finalize();     // == sha256(file)
let shingles = shingler.finish_vec();
```

```python
from lomboksimhash import Sha256State, Shingler

st = Sha256State()
s = Shingler("word", 3)
with open("big.txt", encoding="utf-8") as f:
    for line in f:
        st.update(line.encode("utf-8"))
        s.feed(line)
print(st.hexdigest())
print(s.finish()[:5])
```

### 3.3 Menyetel ambang LSH

`threshold ≈ (1/bands)^(1/rows)`:

| bands × rows | num_perm | threshold ≈ | Artinya |
|---|---|---|---|
| 10 × 10 | 100 | 0.794 | ketat — hanya pasangan sangat mirip |
| 20 × 5 | 100 | 0.549 | seimbang (default) |
| 5 × 20 | 100 | 0.451 | longgar — recall tinggi, kandidat lebih banyak |

### 3.4 Karakter vs Word shingle — kapan pakai apa

- **Word** (n=2..4): teksprosa, near-duplicate semantik, tahan rotasi kata.
- **Character** (n=3..5): teks pendek, judul, tahan typo kecil, bahasa tanpa
  spasi (CJK) — ingat mode ini memotong **code point**, bukan byte.

### 3.5 Menangani error [KODE]

```typescript
import { MinHasher } from 'lomboksimhash';
try {
  new MinHasher(0);
} catch (e) {
  console.log((e as Error).message); // [ERR_MINHASH_PERM] num_perm must be > 0
}
```

```python
from lomboksimhash import LshIndex
try:
    LshIndex(0, 5)
except ValueError as e:
    print(e)  # [ERR_LSH_CONFIG] bands and rows must be > 0
```

## 4. Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| `[ERR_SIG_LEN] signature length must be bands * rows = 100` | `num_perm` ≠ `bands*rows` | Samakan: `MinHasher(100)` untuk `LshIndex(20, 5)` |
| `[ERR_SHINGLE_N]` | `n = 0` / negatif | Pakai `n >= 1` |
| Hasil hash beda dengan contoh | Input tidak di-encode UTF-8 sama, atau token berbeda | Pastikan teks yang sama persis; untuk byte mentah pakai API bytes (`fnv1a64(Uint8Array)`) |
| SimHash dua teks "mirip" tapi Hamming besar | SimHash sensitif terhadap perubahan token — satu kata ganda menggeser banyak bit | Naikkan toleransi atau pakai MinHash+Jaccard |
| PHP fatal `gmp_pow` / segfault | Build PHP GMP lama / ext-gmp tidak ada | Install `ext-gmp`; versi 0.1.0 sudah menghindari `gmp_pow(2, 64)` |
| Jaccard = 0 padahal set sama | Dua MinHasher punya `num_perm` berbeda | Panjang signature harus sama (`[ERR_JACCARD_LEN]` menangkap ini) |
| Teks dengan zero-width space tidak terpisah | U+200B/U+FEFF bukan whitespace kontrak | Bersihkan input sendiri sebelum tokenize (perilaku disengaja & konsisten lintas bahasa) |

## 5. Verifikasi hasil

Setiap port dapat diverifikasi terhadap vector resmi:

```bash
cargo test --test vectors            # Rust
npm test                             # TypeScript (vitest)
pytest ports/python/tests            # Python
go test ./ports/go/...               # Go
cd ports/php && vendor/bin/phpunit   # PHP
```

Semua harus hijau pada mesin apa pun — inilah jaminan bit-identical.
