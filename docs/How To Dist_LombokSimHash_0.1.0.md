# How To Dist — LombokSimHash 0.1.0

Prosedur build, publish per registry, verifikasi pasca-rilis, dan rollback.

> **ATURAN EKOSISTEM**: publikasi HANYA saat owner memintanya eksplisit.
> `npm publish` selalu `--access public` setelah `npm whoami` terverifikasi
> dan versi belum ada di registry. Jangan pernah publish tanpa konfirmasi.

---

## 1. Prasyarat rilis (checklist)

```bash
# 1) Semua gate hijau di lokal
cargo fmt --all -- --check && cargo clippy --all-targets --all-features -- -D warnings && cargo test
(cd ports/typescript && npm ci && npm test && npm run build)
(cd ports/python && python3 -m pytest tests/ && ruff check src tests && mypy src)
(cd ports/go && go vet ./... && go test ./...)
(cd ports/php && vendor/bin/phpunit && vendor/bin/phpstan analyse)

# 2) Vector deterministik
python3 vectors/generate_vectors.py --check

# 3) Versi konsisten di SEMUA manifest (harus sama dengan tag)
grep -m1 version Cargo.toml                        # 0.1.0
grep -m1 '"version"' ports/typescript/package.json
grep -m1 'version' ports/python/pyproject.toml
grep -m1 'version' ports/php/composer.json

# 4) Changelog terisi + docs pack diperbarui
```

## 2. Build artefak

| Target | Perintah | Hasil |
|---|---|---|
| Rust crate | `cargo package --locked` · `cargo build --release` | `target/package/lomboksimhash-0.1.0.crate` · binary CLI |
| npm | `cd ports/typescript && npm ci && npm run build && npm pack` | `lomboksimhash-0.1.0.tgz` (dual ESM+CJS+types) |
| Python | `cd ports/python && python3 -m build` | `dist/*.whl` + `dist/*.tar.gz` |
| Go | `go build ./...` (module `ports/go`) | tidak ada artefak biner — sumber via module proxy |
| PHP | tidak ada build | sumber via Packagist/git |

## 3. Smoke-test wajib SEBELUM publish

```bash
# npm: install tarball ke folder bersih, uji ESM + CJS
mkdir /tmp/smoke-npm && cd /tmp/smoke-npm && npm init -y >/dev/null
npm install /path/to/lomboksimhash-0.1.0.tgz
node -e "import('lomboksimhash').then(m => console.log(m.simhash64Text('the quick brown fox jumps over the lazy dog').toString(16)))"
# → cab7991c5475edee
node -e "const m = require('lomboksimhash'); console.log(m.hamming64(m.simhash64Text('abc'), m.simhash64Text('abc')))"
# → 0

# Python: venv bersih + wheel
python3 -m venv /tmp/smoke-py && /tmp/smoke-py/bin/pip install dist/*.whl
/tmp/smoke-py/bin/python -c "from lomboksimhash import simhash64_text; print(f'{simhash64_text(\"the quick brown fox jumps over the lazy dog\"):016x}')"
# → cab7991c5475edee

# Rust: CLI
./target/release/lomboksimhash-cli simhash "the quick brown fox jumps over the lazy dog"
# → cab7991c5475edee
```

## 4. Publish per registry (saat diminta eksplisit)

### 4.1 npm (target utama ekosistem — Category B)
```bash
npm whoami                 # WAJIB terverifikasi dulu
npm view lomboksimhash version   # pastikan 0.1.0 belum ada (E404)
cd ports/typescript
npm publish --access public --provenance
```
Automasi: tag `v0.1.0` → `.github/workflows/release-npm.yml`
(`npm ci` → typecheck → build → test+coverage → pack dry-run → publish).
Butuh secret `NPM_TOKEN`.

### 4.2 crates.io
```bash
cargo login                       # token sekali
cargo publish --locked
```
Automasi: `release-crates.yml` (fmt+clippy+test+no_std+dry-run dulu).
Butuh secret `CARGO_REGISTRY_TOKEN`.

### 4.3 PyPI (trusted publishing)
Automasi: `release-pypi.yml` (OIDC `id-token: write`; build sdist+wheel,
smoke wheel, publish). Manual: `twine upload dist/*`. Konfigurasi trusted
publisher di PyPI → repo+workflow+environment.

### 4.4 Packagist
Cukup push tag GitHub; daftarkan repo sekali di packagist.org
(`codinglombok/lomboksimhash`); Packagist membaca tag. Verifikasi:
`composer show codinglombok/lomboksimhash`.

### 4.5 Go
Tidak ada "publish" — module proxy menarik dari tag git. Karena module berada
di subpath, pastikan tag memiliki prefix path:
```bash
git tag ports/go/v0.1.0
git push origin ports/go/v0.1.0
```
Verifikasi: `go get github.com/codinglombok/LombokSimHash/ports/go@ports/go/v0.1.0`.

## 5. Verifikasi pasca-rilis

```bash
npm view lomboksimhash dist.tarball    # URL tarball resmi
npm install lomboksimhash@0.1.0 && node -e "console.log(require('lomboksimhash').simhash64Text('abc').toString(16))"
pip install lomboksimhash==0.1.0
cargo install lomboksimhash --version 0.1.0 --locked  # bila diinginkan
composer show -a codinglombok/lomboksimhash
```
Bandinkan hex output dengan vector (`cab7991c5475edee` untuk kalimat fox).

## 6. Rollback / yawning patch

1. **npm**: `npm deprecate lomboksimhash@0.1.0 "reason"`; unpublish hanya
   dalam 72 jam & tanpa dependen (npm policy) — praktik ekosistem: PUBLISH
   PATCH 0.1.1, jangan unpublish.
2. **crates.io**: tidak bisa dihapus — `cargo yank --vers 0.1.0` + rilis 0.1.1.
3. **PyPI**: yank via web UI + rilis 0.1.1.
4. **Prosedur hotfix**: fix di `main` → bump patch di semua manifest →
   changelog `[0.1.1]` → ulangi checklist §1–§5 → tag `v0.1.1`.

## 7. Blocker ekosistem

Setelah `lomboksimhash@0.1.0` tersedia di npm: **LombokEncryptDecrypt**
menambahkan `"lomboksimhash": "^0.1.0"` ke `optionalDependencies`
(BLOCKER LED #1 terbuka).
