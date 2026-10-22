# Contributing to LombokSimHash

Thank you for your interest in contributing! LombokSimHash is a
cross-language library with one hard rule above everything else:
**the same input must produce bit-identical hashes in every port**.
Every contribution, no matter how small, is measured against that contract.

## Project layout

| Path | Contents |
|------|----------|
| `src/` | Rust core (the reference implementation, `no_std` compatible) |
| `ports/typescript` · `ports/python` · `ports/go` · `ports/php` | Language ports |
| `vectors/` | Shared test vectors + deterministic generator (`generate_vectors.py`) |
| `docs/` | Documentation pack (SPEC, API, guides — some docs are local-only by design) |

## The golden rule: vectors first

The shared vector file `vectors/lomboksimhash-vectors-v2.json` is the single
source of truth for behavior. It is **generated, never hand-edited**:

1. Change the algorithm? → change `vectors/generate_vectors.py` **in the same
   commit**, regenerate the vectors, and update every port + the SPEC.
2. Change a port only? → the vectors must still pass unchanged. If a port
   disagrees with the vectors, the port is wrong — not the vector.
3. CI re-verifies byte-identical regeneration on every push
   (`vectors-determinism` job). A failing determinism check is a blocker.

## Local development

Every port must pass its full gate before you open a PR:

```bash
# Rust (reference implementation)
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test
cargo build --no-default-features          # no_std must keep compiling

# TypeScript
cd ports/typescript && npm ci
npm run typecheck && npm test && npm run build

# Python
cd ports/python && pip install -e ".[dev]"
ruff check src tests && mypy src && pytest tests/

# Go
cd ports/go && go vet ./... && go test ./...

# PHP
cd ports/php && composer update
vendor/bin/phpstan analyse --no-progress && vendor/bin/phpunit
```

## Ground rules

- **Zero runtime dependencies.** Every port is a pure implementation; only
  dev-time tooling (test runners, linters) may pull dependencies.
- **Fail closed.** Errors use the uniform `[KODE] message` contract — never
  panic, never return a silently wrong value.
- **Fixed constants.** FNV-1a, the LCG seed, and the Mersenne prime in the
  MinHash implementation are contract, not configuration. Do not "improve" them.
- **Releases are owner-driven.** Publishing to npm, PyPI, crates.io, or GitHub
  Packages happens only on a maintainer-tagged release; PRs never publish.

## Submitting

1. Open an issue describing the problem or proposal (behavior changes need
   discussion before code).
2. Fork, create a feature branch, make your change with tests.
3. Run all gates listed above.
4. Open a pull request referencing the issue; keep the diff focused.

Apache 2.0 applies to every contribution (see [LICENSE](LICENSE)).
