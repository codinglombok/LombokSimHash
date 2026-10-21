# Language — LombokSimHash 0.1.0

Peta port per bahasa: peran, lokasi, vector, catatan platform.

---

## Matriks port

| Port | Status | Lokasi | Vector | Toolchain ketat | Publikasi |
|---|---|---|---|---|---|
| **Rust (acuan)** | ✅ lengkap | `src/` | `tests/vectors.rs` | clippy -D warnings, fmt | crates.io |
| **TypeScript** | ✅ lengkap (prioritas npm) | `ports/typescript/` | `src/vectors.test.ts` | tsc --strict | **npm `lomboksimhash`** (jalur publikasi utama) |
| **Python** | ✅ lengkap | `ports/python/` | `tests/test_vectors.py` | ruff, mypy strict | PyPI |
| **Go** | ✅ lengkap | `ports/go/` | `vectors_test.go` | go vet, gofmt | module proxy (tag `ports/go/v*`) |
| **PHP** | ✅ lengkap | `ports/php/` | `tests/VectorsTest.php` | phpstan max | Packagist |
| C# | ❌ belum — guard `hashFiles` siap | (belum ada) | — | dotnet analyzers | — |
| Kotlin | ❌ belum — guard `hashFiles` siap | (belum ada) | — | detekt, ktlint | — |

> DELTA B: port TS wajib dan menjadi jalur publikasi npm ekosistem; port lain
> mengikuti prioritas README. Port yang belum dikerjakan dipagari di CI
> (hashFiles → skipped), bukan dihapus.

## Peran & keunikan tiap port

### Rust — bahasa acuan
- **Peran**: mematok kontrak; `#![cfg_attr(not(feature = "std"), no_std)]`
  + `extern crate alloc`.
- **Platform**: embedded/WASM (core + alloc saja).
- **Catatan**: `threshold()` LSH memakai Newton–Raphson (tanpa `powf`);
  `vec!` tidak dipakai di jalur no_std; aritmetika MinHash pakai `u128`.
- **Vector**: `tests/vectors.rs` membaca vector via `serde_json` (dev-dep saja).

### TypeScript — jalur npm
- **Peran**: paket npm ekosistem; konsumen utama = LombokEncryptDecrypt (LED #1).
- **Platform**: Node ≥ 18 (BigInt, TextEncoder global); dual build
  `dist/esm` (import) + `dist/cjs` (require) lewat field `exports`.
- **Catatan**: 64-bit = `bigint`; sorting memakai komparator code point
  eksplisit (urutan default JS = UTF-16 code unit — salah untuk non-BMP);
  tokenizer regex khusus (bukan `\s` yang juga cocok U+FEFF).

### Python
- **Peran**: port referensi untuk tooling data/ML (pipeline RAG umumnya Python).
- **Platform**: CPython ≥ 3.10 (3.9 EOL); zero-dep; sdist+wheel PEP 621.
- **Catatan**: modul privat `_sha256/_shingle/_simhash/_minhash/_lsh` agar
  nama fungsi publik tidak menutupi modul; `__future__ annotations` aktif;
  `int` bawaan = aritmetika besar gratis.

### Go
- **Peran**: port untuk layanan backend Go.
- **Platform**: module path `github.com/codinglombok/LombokSimHash/ports/go`
  (module di subdirektori — pola monorepo poliglot).
- **Catatan**: `math/bits` untuk rotate/popcount/Mul64; universal hash memakai
  reduksi `(hi<<3 | lo>>61) + lo&M — terverifikasi 2.000.120 kasus vs big.Int`;
  panic dengan pesan `[KODE]` (konvensi Go untuk programmer error).

### PHP
- **Peran**: port untuk stack PHP (CMS/PHPUnit pipelines).
- **Platform**: PHP ≥ 8.1 + `ext-gmp` + `ext-mbstring`.
- **Catatan**: 64-bit = `\GMP`; SHA-256 via `hash()` (identik FIPS 180-4);
  **dilarang** `gmp_pow(2, 64)` — exponent ≥ 64 melempar `ValueError` pada
  beberapa build (semua konstanta besar lewat `gmp_init("…")`); LSH sebagai
  class terpisah `LshIndex`.

## Cara menambah port baru (SOP)

1. Baca `docs/SPEC_LombokSimHash_0.1.0.md` §5 (algoritma byte-precise) dan §6 (error).
2. Buat `ports/<lang>/` mengikuti pola port lain; konsumsi
   `vectors/lomboksimhash-vectors-v2.json` — **jangan** buat vector sendiri.
3. Implementasikan konstanta persis (SPEC §4); tokenizer eksplisit (§5.3);
   sorting code point; error `[KODE]` byte-identical.
4. Jalankan seluruh 75 kasus → harus hijau; tambahkan error-contract tests.
5. Toolchain ketat bahasa tersebut lulus (S5).
6. Tambahkan job CI dengan guard `if: ${{ hashFiles('ports/<lang>/**') != '' }}`.
7. Perbarui `Language_*.md`, README tabel install, dan `Map_*.md`.

## Kompatibilitas versi vector

- Schema vector: `lomboksimhash-vectors-v2`. Semua port HARUS menolak schema
  tak dikenal (fail-closed) — lihat asersi `schema` di tiap test.
- Upgrade schema = bump file ke `vectors-v3` + regenerate + perbarui semua
  port dalam satu commit (kontrak baru, semver minor).
