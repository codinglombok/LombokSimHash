# Changelog

All notable changes to LombokSimHash will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **GitHub Packages publishing** — new `release-github.yml` workflow, triggered
  automatically when a GitHub Release is published (plus `workflow_dispatch`
  for targeted re-runs):
  - npm mirror `@codinglombok/lomboksimhash` on `npm.pkg.github.com`
    (scoped name applied at CI time; `GITHUB_TOKEN`, zero extra secrets)
  - Container image `ghcr.io/codinglombok/lomboksimhash` — static musl
    binary on `FROM scratch`, tags `vX.Y.Z` / `X.Y` / `latest`
- `Dockerfile` + `.dockerignore` — two-stage build (`rust:1-alpine` → `scratch`)
- Community health files: `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`
- Version badges (npm / PyPI / crates.io) and a Mirrors section in the README
- `Cargo.lock` is now committed (binary crate + `cargo package --locked`
  reproducibility); removed from `.gitignore`

### Fixed
- **Release to PyPI**: wheel smoke-test asserted the wrong constant —
  `simhash64_text("the fox")` is `54b080184441c10c` (the previous `edee`
  suffix belongs to the pangram `"the quick brown fox jumps over the lazy
  dog"` = `cab7991c5475edee`). Assertion now pins the full canonical value
- **CI**: PHP matrix dropped 8.1 (EOL; phpunit ^11.5 requires >= 8.2),
  `composer.json` aligned to `>= 8.2`; workflow-validity startup failures
  fixed by moving `hashFiles` out of job-level `if` into a guard job;
  `actions/checkout` bumped v4 → v5

## [0.1.0] — 2026-10-21

### Added
- **SimHash** — 64-bit and 128-bit text fingerprinting via FNV-1a weighted bit accumulation
- **MinHash** — Jaccard similarity estimation with k-permutation universal hash family
- **LSH** — Band+row locality-sensitive hashing for approximate nearest neighbor search
- **SHA-256** — Pure implementation (FIPS 180-4) for exact content deduplication,
  including streaming `Sha256State`
- **Shingling** — Character and word n-gram generation with streaming API
- **CLI tool** — `lomboksimhash-cli` for command-line usage (Rust, requires `std` feature)
- Deterministic cross-language test vectors — `vectors/generate_vectors.py`
  generates `vectors/lomboksimhash-vectors-v2.json` (75 cases, exact bit-identical
  hex: SHA-256 boundary padding, UTF-8 multi-byte, exact MinHash signatures,
  SimHash128 hi/lo, LSH band keys and index scenarios); CI re-verifies determinism
- Language ports:
  - **Rust** (core) — `no_std` compatible (core + alloc), zero dependencies
  - **TypeScript** — Pure implementation with BigInt for 64-bit math, dual ESM + CJS build
  - **Python** — Pure implementation, zero dependencies, src-layout
  - **Go** — Pure implementation using `math/bits`
  - **PHP** — Implementation using GMP extension for 64-bit math
- Uniform error contract across all ports — `[KODE] pesan`, fail-closed
  (`[ERR_SHINGLE_N]`, `[ERR_MINHASH_PERM]`, `[ERR_LSH_CONFIG]`, `[ERR_SIG_LEN]`,
  `[ERR_JACCARD_LEN]`, `[ERR_JACCARD_EMPTY]`)
- Explicit cross-language tokenizer contract (Unicode White_Space, 25 code points) —
  `tokenize()` exposed in every port; language built-ins are deliberately overridden
- GitHub Actions CI for 5 languages + vectors-determinism job, with `hashFiles`
  guards per ecosystem standard S6
- Coverage thresholds: TS ≥95% stmt / ≥90% branch (vitest+c8), Python ≥95% combined
  with branch (pytest-cov), Go ≥95% statements (coverprofile gate), Rust ≥95% lines
  (cargo-llvm-cov in CI)
- Strict toolchains: `cargo clippy -D warnings` + `cargo fmt --check`, `tsc --strict`,
  `ruff` + `mypy --strict`, `go vet` + gofmt check, `phpstan --level=max`
- Apache 2.0 license

### Changed
- **PHP**: replaced `gmp_pow(2, 64)` with `gmp_init` constants — `gmp_pow` throws
  `ValueError` for exponent ≥ 64 on several PHP builds, which previously crashed
  the whole port
- **PHP**: LSH moved from ad-hoc instance methods on `LombokSimHash` to a dedicated
  `CodingLombok\LombokSimHash\LshIndex` class
- **TypeScript**: package now ships dual ESM (`dist/esm`) + CJS (`dist/cjs`) via
  `exports` map; test runner migrated to vitest with coverage thresholds; `npm ci`
  with committed `package-lock.json`
- **Python**: package migrated to `src/` layout with private modules
  (`_sha256`, `_shingle`, `_simhash`, `_minhash`, `_lsh`); public API unchanged;
  `requires-python` bumped to >= 3.10 (3.9 EOL October 2025)
- **Go**: import path corrected to `github.com/codinglombok/LombokSimHash/ports/go`
  (the module lives at `ports/go`); `Insert`/`Query`/`Remove` now validate signature
  length with `[ERR_SIG_LEN]` instead of panicking with a slice error
- **LSH `query()`** returns candidates sorted ascending by code point in ALL ports
  (TypeScript previously returned insertion order)
- Test vectors upgraded from approx-only v1 to exact bit-identical v2 (see Removed)

### Deprecated
- *(nothing)*

### Removed
- `vectors/lomboksimhash-vectors-v1.json` — superseded by the generated, exact
  vectors-v2 (v1 was hand-typed, contained no generator, and only approximate
  MinHash/LSH assertions)

### Fixed
- **Rust `no_std` build broken**: `vec![]` macro unavailable without `alloc` prelude
  (`src/minhash.rs`) and `f64::powf` std-only (`src/lsh.rs`) — replaced with
  `Vec::resize` and a Newton–Raphson n-th root (accuracy ≥ 1e-12)
- **PHP port crashed on first test** (see Changed: `gmp_pow`)
- README badge pointed to non-existent `masterplan_repo.md`; Go install instructions
  pointed to a non-fetchable module path
- GitHub Actions CI Rust job was red: `cargo fmt --check` and `cargo clippy -D
  warnings` both failed (5 clippy lints fixed: `Default` impl for `Sha256State`,
  `needless_range_loop` ×2, `or_insert_with`, unused import)

### Security
- No secrets in repo; all inputs fail closed; no dynamic evaluation of untrusted
  input in any port

### Technical Details
- Deterministic cross-language reproducibility via fixed LCG seed (`0x517cc1b727220a95`)
- FNV-1a 64-bit as token hash function (offset: `0xcbf29ce484222325`, prime: `0x100000001b3`)
- Mersenne prime `2^61 - 1` for universal hash family in MinHash
- All hash values verified bit-identical across Rust, TypeScript, Python, Go, PHP
  against the shared vector file

[0.1.0]: https://github.com/codinglombok/LombokSimHash/releases/tag/v0.1.0
