# Development Idea — LombokSimHash 0.1.0

Backlog ide terurut prioritas (P0 = kritis, P3 = nanti), lengkap dengan
kriteria selesai dan non-goals. Sumber: temuan audit 2026-10-21 + arah
ekosistem LombokRAGFrameworks.

---

## P0 — Dampak langsung ke rilis

### P0-1 · Port tambahan: C# dan Kotlin (guard CI)
Ekosistem targetnya lintas bahasa penuh; dua permintaan paling sering.
- **Kriteria selesai**: port lulus `vectors-v2` penuh; toolchain ketat
  (dotnet format + analyzers / detekt + ktlint); job CI dengan guard
  `hashFiles` sesuai S6; hasil bit-identical (hex).
- **Estimasi**: 2–3 hari/port (algoritma sudah dipatok SPEC).

### P0-2 · Benchmark resmi per port
Keputusan ambang Hamming & ukuran LSH butuh angka, bukan intuisi.
- **Kriteria selesai**: benchmark criterion/ criterion (Rust), vitest bench
  (TS), pytest-benchmark (Py), Go bench; laporan throughput (MB/s) & latency
  p50/p99 untuk 1 KB–10 MB; masuk `docs/` versi berikutnya.
- **Estimasi**: 2 hari.

### P0-3 · Release automation lengkap
- **Kriteria selesai**: satu tag `v*` memicu npm + crates.io + PyPI
  (semua sudah diguard); Go: GoReleaser + tag module path `ports/go`;
  provenance npm (provenance: true); smoke-test pasca-publish otomatis.
- **Estimasi**: 1 hari.

## P1 — Kekokohan & DX

### P1-1 · Property-based testing lebih dalam
- **Kriteria selesai**: proptest (Rust) + fast-check (TS) + hypothesis (Py):
  tokenize invers (join≈split), simhash deterministik atas permutasi token,
  LSH recall ≥ p95 pada Jaccard ≥ threshold − ε; dijalankan nightly CI.
- **Estimasi**: 2 hari.

### P1-2 · Vector v3: fuzz determinisme lintas platform
- **Kriteria selesai**: generator memproduksi 10.000 kasus acak ter-seed
  (termasuk non-BMP, pemisah whitespace campuran); semua port lulus;
  ukuran file tetap < 2 MB ( NDJSON terkompresi atau hash-driven sampling).
- **Estimasi**: 1–2 hari.

### P1-3 · Simhash128 serialisasi tunggal (u128 natif)
- **Kriteria selesai**: API opsional `simhash128_hex(text) -> 32-char hex`
  di semua port tanpa mengekpos pasangan; backward compatible.
- **Estimasi**: 0.5 hari.

### P1-4 · Dokumentasi interaktif
- **Kriteria selesai**: playground web (WASM dari core Rust) yang menampilkan
  SimHash live; hasil hex identik dengan port lain (bukti visual SPEC).
- **Estimasi**: 2 hari.

## P2 — Fitur

### P2-1 · MinHash tanpa alokasi ulang (add_many batch)
- Satu pass FNV untuk banyak token dengan buffer reuse; API `add_tokens`
  tetap; kriteria: tanpa perubahan hasil vector; benchmark ≥ 30% lebih cepat
  pada 10k token.

### P2-2 · LSH persistable (export/import bucket)
- Serialisasi deterministik bucket (JSON/NDJSON) — bit-identical lintas
  bahasa; kriteria: round-trip di port A → port B menghasilkan query sama.

### P2-3 · Mode Normalisasi teks opsional (NFC, lowercase)
- Kontrak baru → butuh SPEC v2, vector v3, bump minor (0.2.0). Non-default.

### P2-4 · Weighted SimHash (bobot token)
- Berguna untuk judul vs isi; butuh kontrak bobot deterministik (fixed-point).

## P3 — Jangka panjang

### P3-1 · SIMD jalur FNV (AVX2/NEON/WASM)
- Wajib hasil identik dengan jalur skalar (DELTA B); kriteria: vector penuh
  lulus pada kedua jalur + CI matrix dengan/ tanpa fitur.

### P3-2 · no_std penuh untuk `lsh.rs` tanpa alloc (fixed-size buckets)
- Buka jalur embedded; kriteria: build untuk `thumbv7em-none-eabihf`.

### P3-3 · Integrasi ekosistem
- `optionalDependencies` di LombokEncryptDecrypt (BLOCKER LED #1) → setelah
  npm publish 0.1.0; adapter LombokChunker (chunk → dedup pipeline).

## Non-goals (dengan sengaja)

1. **Kriptografi** — SHA-256 di sini untuk dedup, bukan keamanan; tidak ada
   HMAC/KDF/MAC. Gunakan pustaka kripto khusus.
2. **Bahasa alami lanjutan** — stemming/lemmatization/stopword TIDAK masuk
   pustaka ini (normalisasi bertanggung jawab pada pemanggil).
3. **Distribusi** — LSH hanya berkandidat; tidak ada ann servis jaringan,
   tidak ada server, tidak ada I/O file.
4. **Dependency runtime** — tetap nol di semua port, selamanya (S1).
5. **Presisi float lintas bahasa** — `threshold()` tetap informasional;
   tidak akan dijadikan kontrak bit-identical.
