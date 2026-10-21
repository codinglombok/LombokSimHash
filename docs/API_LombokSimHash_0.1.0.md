# API — LombokSimHash 0.1.0

Referensi lengkap semua ekspor publik per bahasa. Kontrak perilaku:
`docs/SPEC_LombokSimHash_0.1.0.md`. Semua port diuji terhadap
`vectors/lomboksimhash-vectors-v2.json` (bit-identical).

Format error di SEMUA bahasa: `[KODE] pesan` — pesan byte-identical.
Pemetaan: Rust `panic!`, Go `panic`, TypeScript `throw new Error`,
Python `raise ValueError`, PHP `throw InvalidArgumentException`.

---

## 1. SHA-256

| Bahasa | Signature |
|---|---|
| Rust | `pub fn sha256(data: &[u8]) -> [u8; 32]` · `pub fn to_hex(hash: &[u8]) -> String` |
| TypeScript | `function sha256(input: string \| Uint8Array): string` |
| Python | `def sha256(data: bytes \| str) -> str` |
| Go | `func SHA256(data []byte) string` |
| PHP | `LombokSimHash::sha256(string $data): string` |

- **Parameter**: byte mentah, atau teks (otomatis UTF-8 di TS/Python; Rust menerima
  `&[u8]` — panggil `text.as_bytes()`).
- **Return**: Rust = 32 byte (pakai `to_hex` untuk hex); bahasa lain = hex lowercase 64 char.
- **Streaming**: Rust `Sha256State::{new, update, finalize}` + `Default`;
  Python `Sha256State::{update, digest, hexdigest, finalize}`.
- Contoh:
  - Rust: `to_hex(&sha256(b"hello"))` → `2cf24dba5…b9824`
  - TS: `sha256('hello')` → hex 64 char
  - Go: `SHA256([]byte("hello"))`
  - PHP: `LombokSimHash::sha256('hello')`

## 2. FNV-1a 64

| Bahasa | Signature |
|---|---|
| Rust | `pub fn fnv1a64(data: &[u8]) -> u64` |
| TypeScript | `function fnv1a64(data: Uint8Array): bigint` |
| Python | `def fnv1a64(data: bytes) -> int` |
| Go | `func FNV1a64(data []byte) uint64` |
| PHP | `LombokSimHash::fnv1a64(string $data): \GMP` |

Konstanta publik (TS): `FNV64_OFFSET`, `FNV64_PRIME`, `MASK64`.
Return u64 (16 hex): `fnv1a64(b"hello")` = `0xa430d84680aabd0b`.

## 3. Tokenize

| Bahasa | Signature |
|---|---|
| Rust | `pub fn tokenize(text: &str) -> Vec<&str>` · `pub fn is_spec_whitespace(c: char) -> bool` |
| TypeScript | `function tokenize(text: string): string[]` · `SPEC_WHITESPACE: ReadonlySet<number>` |
| Python | `def tokenize(text: str) -> list[str]` · `WHITESPACE: frozenset[str]` |
| Go | `func Tokenize(text string) []string` |
| PHP | `LombokSimHash::tokenize(string $text): array` |

Split pada run karakter Unicode `White_Space` (tepat 25 code point, lihat SPEC §5.3).
U+200B/U+FEFF **tidak** dihitung whitespace. Tanpa error.

## 4. Shingling

| Bahasa | Signature |
|---|---|
| Rust | `Shingler::new(mode: ShingleMode, n: usize)` · `feed(&mut self, text)` · `finish(&self) -> BTreeSet<String>` · `finish_vec()` · `char_shingles(text, n)` · `word_shingles(text, n)` |
| TypeScript | `class Shingler(mode: 'character' \| 'word', n)` · `feed(text)` · `finish(): string[]` · `charShingles(text, n)` · `wordShingles(text, n)` |
| Python | `Shingler(mode='character', n=3)` · `feed(text)` · `finish() -> list[str]` · `char_shingles(text, n)` · `word_shingles(text, n)` |
| Go | `CharShingles(text, n)` · `WordShingles(text, n)` |
| PHP | `LombokSimHash::charShingles($text, $n)` · `wordShingles($text, $n)` |

- **n**: ukuran n-gram, `n >= 1`. `n < 1` → `[ERR_SHINGLE_N] shingle size must be > 0`.
- **Return**: shingle unik **sorted code point**. Jika jumlah elemen < n → list kosong.
- Mode character memotong **code point** (bukan byte); mode word memakai tokenizer §3,
  gabungan dengan satu spasi.
- Streaming: `feed()` menumpuk buffer; `finish()` murni (boleh dipanggil berulang).

## 5. SimHash

| Bahasa | simhash64 | simhash128 | hamming |
|---|---|---|---|
| Rust | `simhash64(tokens: &[&str]) -> u64` · `simhash64_text(text) -> u64` | `simhash128(tokens) -> (u64, u64)` · `simhash128_text` | `hamming64(a, b) -> u32` · `hamming128(a, b) -> u32` |
| TypeScript | `simhash64(tokens: string[]): bigint` · `simhash64Text` | `simhash128(tokens): [bigint, bigint]` · `simhash128Text` | `hamming64(a: bigint, b: bigint): number` · `hamming128(a, b): number` |
| Python | `simhash64(tokens) -> int` · `simhash64_text` | `simhash128(tokens) -> tuple[int, int]` · `simhash128_text` | `hamming64(a, b) -> int` · `hamming128(a, b) -> int` |
| Go | `SimHash64(tokens []string) uint64` · `SimHash64Text` | `SimHash128(tokens) (hi, lo uint64)` · `SimHash128Text` | `Hamming64(a, b uint64) int` · `Hamming128(aHi, aLo, bHi, bLo uint64) int` |
| PHP | `LombokSimHash::simhash64(array $tokens): \GMP` · `simhash64Text` | `simhash128($tokens): array{\GMP, \GMP}` · `simhash128Text` | `hamming64(\GMP $a, \GMP $b): int` · `hamming128(array $a, array $b): int` |

- `simhash64([])` = `0`. `simhash128([])` = `(0, 0)`.
- `*_text` memakai tokenizer §3.
- Representasi 128-bit = pasangan `(hi, lo)`; hex gabungan = `hi ‖ lo` (32 char).
- `hamming128` menghitung `popcount(hi⊕hi) + popcount(lo⊕lo)`.
- Tanpa error (validasi tidak ada di jalur ini).

## 6. MinHash

| Bahasa | Konstruktor | add | signature |
|---|---|---|---|
| Rust | `MinHasher::new(num_perm: usize)` | `add(&mut self, token)` · `add_tokens(&mut self, &[&str])` | `signature(&self) -> &[u64]` · `num_perm()` |
| TypeScript | `new MinHasher(numPerm: number)` | `add(token)` · `addTokens(tokens)` | `signature: bigint[]` · `numPerm` |
| Python | `MinHasher(num_perm=128)` | `add(token)` · `add_tokens(tokens)` | `signature: list[int]` · `num_perm` |
| Go | `NewMinHasher(numPerm int) *MinHasher` | `Add(token)` · `AddTokens(tokens)` | `Signature []uint64` · `NumPerm` |
| PHP | `LombokSimHash::minhash(array $tokens, int $numPerm = 128): list<\GMP>` | — (batch) | array |

- **num_perm < 1** → `[ERR_MINHASH_PERM] num_perm must be > 0`.
- Signature diinisialisasi `2^64 − 1`; `add` idempoten per token (urutan bebas).
- `jaccard_estimate`:
  - Rust `jaccard_estimate(sig_a: &[u64], sig_b: &[u64]) -> f64`
  - TS `jaccardEstimate(sigA: bigint[], sigB: bigint[]): number`
  - Python `jaccard_estimate(sig_a, sig_b) -> float`
  - Go `JaccardEstimate(sigA, sigB []uint64) float64`
  - PHP `LombokSimHash::jaccardEstimate(array $sigA, array $sigB): float`
- Error: `[ERR_JACCARD_LEN] signatures must have same length`,
  `[ERR_JACCARD_EMPTY] signatures must not be empty`.
- Float: hasil `matches/num_perm` IEEE-754 eksak untuk pembagi yang dipakai vector.

## 7. LSH

| Bahasa | Konstruktor | insert | query | remove |
|---|---|---|---|---|
| Rust | `LshIndex::new(bands, rows)` | `insert(doc_id, &[u64])` | `query(&[u64]) -> Vec<String>` | `remove(doc_id, &[u64])` |
| TypeScript | `new LshIndex(bands, rows)` | `insert(docId, bigint[])` | `query(bigint[]): string[]` | `remove(docId, bigint[])` |
| Python | `LshIndex(bands, rows)` | `insert(doc_id, list[int])` | `query(list[int]) -> list[str]` | `remove(doc_id, sig)` |
| Go | `NewLshIndex(bands, rows int) *LshIndex` | `Insert(docID, sig)` | `Query(sig) []string` | `Remove(docID, sig)` |
| PHP | `new LshIndex(int $bands, int $rows)` | `insert($docId, list<\GMP>)` | `query(...) -> list<string>` | `remove(...)` |

- Aksesori: `bands()`, `rows()`, `signature_len()` (TS: `bands`, `rows`, `signatureLen`;
  Python: property), `threshold() -> f64` = `(1/bands)^(1/rows)` (informasional, toleransi 1e-9).
- **bands/rows < 1** → `[ERR_LSH_CONFIG] bands and rows must be > 0`.
- Panjang signature ≠ bands×rows → `[ERR_SIG_LEN] signature length must be bands * rows = {n}`.
- `query()` = gabungan kandidat **unik + sorted code point**.
- `remove(doc_id, sig)` hanya menghapus kemunculan doc_id pada bucket yang tersentuh sig.

## 8. Tabel error lengkap

| Kode | Pemicu | Pesan persis |
|---|---|---|
| `[ERR_SHINGLE_N]` | `n < 1` pada shingling | `shingle size must be > 0` |
| `[ERR_MINHASH_PERM]` | `num_perm < 1` | `num_perm must be > 0` |
| `[ERR_LSH_CONFIG]` | `bands<1` atau `rows<1` | `bands and rows must be > 0` |
| `[ERR_SIG_LEN]` | panjang signature salah pada LSH | `signature length must be bands * rows = {n}` |
| `[ERR_JACCARD_LEN]` | panjang dua signature beda | `signatures must have same length` |
| `[ERR_JACCARD_EMPTY]` | signature kosong pada jaccard | `signatures must not be empty` |
| `[ERR_ARGS]` | CLI kurang argumen | `missing text argument` / `need two text arguments` |
| `[ERR_UNKNOWN_CMD]` | CLI perintah tak dikenal | `unknown command: {cmd}` |

## 9. Contoh ujung-ke-ujung (RAG dedup)

```python
from lomboksimhash import sha256, simhash64_text, hamming64, MinHasher, LshIndex

def is_duplicate(new_text, sha_seen, simhash_seen, lsh, mh_index, max_hamming=3):
    d = sha256(new_text)
    if d in sha_seen:                     # 1) eksak
        return True
    h = simhash64_text(new_text)          # 2) near-duplicate
    for prev in simhash_seen:
        if hamming64(h, prev) <= max_hamming:
            return True
    mh = MinHasher(100)                   # 3) kandidat LSH + Jaccard
    mh.add_tokens(new_text.split())
    if any(j >= 0.8 for j in (
        jaccard_pair(mh, lsh, mh_index) for mh_index in ()
    )):
        return True
    return False
```
(Cookbook lengkap dengan LSH nyata ada di `Guide How to Use_*.md`.)
