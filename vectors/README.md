# vectors/ — Cross-Language Test Vectors

`lomboksimhash-vectors-v2.json` adalah **satu-satunya** file vector resmi.
Semua port (Rust, TypeScript, Python, Go, PHP) mengonsumsi file yang sama
persis dan wajib menghasilkan hasil bit-identical (perbandingan hex, bukan
near-equality).

## Aturan

1. **Jangan pernah mengedit file JSON secara manual.** File ini di-generate
   oleh skrip deterministik:

   ```bash
   python3 vectors/generate_vectors.py          # regenerate
   python3 vectors/generate_vectors.py --check  # verifikasi byte-identical
   ```

2. Skrip generator mengimplementasikan SPEC
   (`docs/SPEC_LombokSimHash_0.1.0.md`) secara independen — bertindak
   sebagai oracle; implementasi acuan (Rust) wajib cocok dengan vector,
   bukan sebaliknya.
3. Output skrip deterministik total (tanpa timestamp/random); CI
   memverifikasi regenerasi menghasilkan byte yang sama.
4. Perubahan kontrak = ubah SPEC → ubah generator → bump `schema`
   (mis. `vectors-v3`) → regenerate → perbarui semua port.

## Struktur kasus

| Bagian | Isi |
|---|---|
| `sha256` | FIPS 180-4: vektor standar, padding boundary 55–65 byte, UTF-8, biner |
| `fnv1a64` | FNV-1a 64: teks + byte mentah (`input_hex`) |
| `shingle` | karakter/kata, edge case n, UTF-8, collapse whitespace |
| `simhash64` / `simhash128` | fingerprint eksak (`hi_hex`/`lo_hex`) |
| `minhash_signature` | signature hex eksak per num_perm |
| `minhash_jaccard` | jumlah kecocokan integer eksak |
| `lsh_bandhash` | kunci bucket FNV-1a atas LE bytes |
| `lsh_index` | skenario insert/query/remove + hasil sorted eksak |

Nilai float (threshold LSH) sengaja TIDAK dimasukkan sebagai vector eksak —
lihat SPEC §11.
