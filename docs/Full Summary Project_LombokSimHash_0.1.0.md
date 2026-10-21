# Full Summary Project — LombokSimHash 0.1.0

Ringkasan eksekutif: tujuan, arsitektur, status vs SPEC, metrik, roadmap.

---

## 1. Tujuan

LombokSimHash adalah pustaka **deteksi dokumen duplikat/near-duplicate** untuk
pipeline RAG di ekosistem LombokRAGFrameworks (Tier 4 Hub). Masalah yang
diselesaikan: vektor store yang dibuang-nafas oleh konten duplikat. Pustaka
ini menyediakan tiga lapis pertahanan — **SHA-256** (duplikat eksak),
**SimHash + Hamming** (near-duplicate murah), **MinHash + LSH + Jaccard**
(kandidat kemiripan terukur) — ditambah **shingling** sebagai unit fitur.

Fungsi kunci ekosistem: satu kontrak algoritma dipatok di bahasa acuan
(**Rust**) + SPEC normatif + file test vector deterministik yang dibagikan
ke semua port lintas bahasa dengan hasil **bit-identical** (perbandingan hex,
bukan near-equality).

## 2. Arsitektur (ringkas)

```
vectors/generate_vectors.py  ← oracle independen (stdlib murni, deterministik)
        │  (menghasilkan)
        ▼
vectors/lomboksimhash-vectors-v2.json   (75 kasus; sumber kebenaran data)
        │  dikonsumsi identik oleh
        ├─ src/*.rs                (Rust — ACUAN; no_std, zero-dep)
        ├─ ports/typescript/src    (dual ESM+CJS; BigInt 64-bit)
        ├─ ports/python/src        (src-layout; modul privat _*.py)
        ├─ ports/go/lomboksimhash.go (math/bits; tabel + property ringan)
        └─ ports/php/src           (GMP; hash() untuk SHA-256)
```

Keputusan arsitektural utama (ADR ringkas — lengkap di `Architecture_*.md`):
1. Tokenizer eksplisit 25 code point `White_Space` di semua port (bawaan bahasa divergensi).
2. Sorting berbasis code point (bukan UTF-16/byte lokal).
3. SimHash128 derivasi kedua = FNV-1a atas `utf8(token) || 0xFF`.
4. MinHash universal hash dengan aritmetika ≥121-bit aman (u128/BigInt/big.Int/GMP).
5. `threshold()` LSH via Newton–Raphson (Rust) agar no_std benar-benar build.
6. Error `[KODE] pesan` byte-identical, fail-closed, tanpa fallback diam.

## 3. Status vs SPEC (0.1.0)

| Area SPEC | Status |
|---|---|
| §4 Konstanta kanonik | ✅ semua port |
| §5.1–5.2 SHA-256 & FNV-1a | ✅ lulus vector (15 + 10 kasus, termasuk boundary padding 55–65 byte) |
| §5.3 Tokenize 25 code point | ✅ diuji unit + implisit vector word-shingle |
| §5.4 Shingling (code point, sorted) | ✅ 14 kasus |
| §5.5–5.6 SimHash 64/128 | ✅ 16 kasus exact hex |
| §5.8 MinHash signature eksak | ✅ 7 kasus (num_perm 8–128, set kosong, duplikat, unicode) |
| §5.9 LSH band+row | ✅ 5 band-hash + 4 skenario index (insert/query/remove) |
| §6 Error `[KODE]` | ✅ diuji unit di 5 port, byte-identical |
| §11 Float | ✅ threshold informasional; jaccard via integer matches |

**Semua port lulus seluruh 75 kasus vector bersama.** Tidak ada divergensi yang
diketahui; perbedaan float (threshold) sudah dipagari SPEC §11.

## 4. Metrik (terukur saat rilis 0.1.0)

| Metrik | Rust | TypeScript | Python | Go | PHP |
|---|---|---|---|---|---|
| Test lulus | 44 (33 unit + 11 vector) | 41 (vitest) | 39 (pytest) | 30+ table-driven | 82 (PHPUnit, 1188 asersi) |
| Coverage | gate CI ≥95% lines¹ | 99.45% stmt / 97.27% branch | 99% (branch-on) | 98.9% stmt | belum ada driver lokal² |
| Toolchain | clippy -D ✓ fmt ✓ | tsc strict ✓ | ruff ✓ mypy strict ✓ | vet ✓ gofmt ✓ | phpstan max ✓ |
| Build | no_std ✓ | dual ESM+CJS ✓ | sdist+wheel ✓ | go build ✓ | composer strict ✓ |
| Dep runtime | 0 | 0 | 0 | 0 | 0 |

¹ `cargo llvm-cov --fail-under-lines 95` dipasang di CI; eksekusi lokal timeout
di lingkungan dev (lihat TECH DEBT TD-01).
² PHPUnit coverage butuh driver (pcov/xdebug); terpasang di CI via setup-php.
PHP coverage gate: menjalankan unit+vector penuh (83 test) tanpa threshold
persentase — dicatat sebagai TD-02.

Artefak distribusi 0.1.0 telah di-build & di-smoke-test:
`lomboksimhash-0.1.0.tgz` (npm; ESM+CJS, 14.3 kB),
`lomboksimhash-0.1.0-py3-none-any.whl` + sdist,
`lomboksimhash-cli` (release binary), crate `cargo package` ready.

## 5. Roadmap (ringkas; detail di Masterplan & Development Idea)

- **0.1.x**: hardening (benchmark resmi, property-based nightly, GoReleaser).
- **0.2.0**: normalisasi opsional (NFC/lowercase) + LSH persistable — kontrak
  baru via SPEC v2/vectors v3, semver minor.
- **1.0.0**: kriteria — 2 kuartal tanpa perubahan kontrak, ≥2 port tambahan
  (C#/Kotlin), SIMD jalur identik dengan skalar, playground WASM.

## 6. Risiko utama

1. **Divergensi build PHP GMP antar platform** — sudah dipagari (tanpa
   `gmp_pow` exponent ≥ 64), tapi butuh CI matrix PHP 8.1–8.3 aktif (sudah ada).
2. **Module path Go** di `ports/go` — sedikit tidak lazim; didokumentasikan
   di README + SPEC §10; GoReleaser akan menyempurnakan.
3. **Ketergantungan pada file vector bersama** — semua port harus tetap
   membaca satu file; CI vectors-determinism job menjaga regenerasi.
