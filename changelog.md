# Changelog

All notable changes to LombokSimHash will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-09-18

### Added
- **SimHash** — 64-bit and 128-bit text fingerprinting via FNV-1a weighted bit accumulation
- **MinHash** — Jaccard similarity estimation with k-permutation universal hash family
- **LSH** — Band+row locality-sensitive hashing for approximate nearest neighbor search
- **SHA-256** — Pure implementation (FIPS 180-4) for exact content deduplication
- **Shingling** — Character and word n-gram generation with streaming API
- **CLI tool** — `lomboksimhash-cli` for command-line usage (Rust, requires `std` feature)
- Cross-language test vectors (`vectors/lomboksimhash-vectors-v1.json`)
- Language ports:
  - **Rust** (core) — `no_std` compatible, zero dependencies
  - **TypeScript** — Pure implementation with BigInt for 64-bit math
  - **Python** — Pure implementation, zero dependencies
  - **Go** — Pure implementation using `math/bits`
  - **PHP** — Implementation using GMP extension for 64-bit math
- GitHub Actions CI/CD workflows for all 5 languages
- Registry configuration for crates.io, npm, PyPI, Packagist, Go modules
- Apache 2.0 license

### Technical Details
- Deterministic cross-language reproducibility via fixed LCG seed (`0x517cc1b727220a95`)
- FNV-1a 64-bit as token hash function (offset: `0xcbf29ce484222325`, prime: `0x100000001b3`)
- Mersenne prime `2^61 - 1` for universal hash family in MinHash
- All hash values verified identical across Rust, TypeScript, Python, Go, PHP

[0.1.0]: https://github.com/codinglombok/LombokSimHash/releases/tag/v0.1.0
