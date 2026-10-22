# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |
| < 0.1.0 | ❌ (never publicly released) |

## Reporting a vulnerability

**Please do not open a public issue for security reports.**

Contact: **codinglombok@gmail.com** (maintainer of the Lombok Ecosystem).

Include: affected port(s) and version, a minimal reproduction, and your
assessment of impact. You will receive an acknowledgment within **5 business
days**, and a fix or a mitigation plan within **30 days** for confirmed
issues. Credit is given in the changelog unless you prefer otherwise.

## Scope and honest boundaries

LombokSimHash provides hashing primitives (SimHash, MinHash, LSH, SHA-256,
shingling) for **near-duplicate detection**, not for secrecy.

- **SHA-256** here is a pure, constant-free reimplementation of FIPS 180-4
  intended for exact-duplicate checks. For cryptographic authentication or
  signatures, use a maintained, audited crypto library.
- **SimHash / MinHash / LSH** are similarity sketches — they are *designed*
  to be probabilistic and must never be used for security decisions
  (authorization, integrity, proofs).
- All ports fail closed on invalid configuration (uniform `[KODE] message`
  errors) and perform no dynamic evaluation of untrusted input.

## Supply chain

- Packages are published from GitHub Actions only (`release-*.yml`), driven by
  maintainer tags/releases — never from PRs.
- npm: `lomboksimhash` (primary) and `@codinglombok/lomboksimhash` (GitHub
  Packages mirror). PyPI: `lomboksimhash` (trusted publishing, OIDC).
  crates.io: `lomboksimhash`. Container: `ghcr.io/codinglombok/lomboksimhash`.
- Runtime dependencies: **zero** in every published artifact; test tooling
  dependencies are monitored by Dependabot.
