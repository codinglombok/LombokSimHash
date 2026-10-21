#!/usr/bin/env python3
"""Deterministic cross-language test vector generator for LombokSimHash.

Implements the contract in docs/SPEC_LombokSimHash_0.1.0.md directly
(independent oracle — the Rust reference implementation must match these
vectors, not the other way around).

Rules:
- Pure Python stdlib. Zero third-party dependencies.
- Fully deterministic: no timestamps, no randomness, stable ordering.
  Re-running this script must reproduce the committed JSON byte-identically.

Usage:
    python3 vectors/generate_vectors.py            # writes vectors-v2.json
    python3 vectors/generate_vectors.py --check    # verify byte-identical
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "lomboksimhash-vectors-v2.json"

# ---------------------------------------------------------------------------
# SPEC constants
# ---------------------------------------------------------------------------
FNV64_OFFSET = 0xCBF29CE484222325
FNV64_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1
MERSENNE_61 = (1 << 61) - 1
LCG_SEED = 0x517CC1B727220A95
LCG_MUL = 6364136223846793005
LCG_INC = 1442695040888963407

# SPEC whitespace set = Unicode White_Space property (25 code points).
WHITESPACE = frozenset(
    "\t\n\x0b\x0c\r \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005"
    "\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
)


# ---------------------------------------------------------------------------
# Oracle implementation of the SPEC
# ---------------------------------------------------------------------------
def fnv1a64(data: bytes) -> int:
    h = FNV64_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV64_PRIME) & MASK64
    return h


def tokenize(text: str) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []
    for ch in text:
        if ch in WHITESPACE:
            if cur:
                parts.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


def h64(value: int) -> str:
    return f"{value:016x}"


def shingles(text: str, mode: str, n: int) -> list[str]:
    if n < 1:
        raise ValueError("[ERR_SHINGLE_N] shingle size must be > 0")
    if mode == "character":
        elems = list(text)  # code points
        sep = ""
    elif mode == "word":
        elems = tokenize(text)
        sep = " "
    else:
        raise ValueError(f"bad mode: {mode}")
    out = {sep.join(elems[i:i + n]) for i in range(len(elems) - n + 1)}
    return sorted(out)


def simhash64(tokens: list[str]) -> int:
    v = [0] * 64
    for token in tokens:
        h = fnv1a64(token.encode("utf-8"))
        for i in range(64):
            if (h >> i) & 1:
                v[i] += 1
            else:
                v[i] -= 1
    result = 0
    for i in range(64):
        if v[i] > 0:
            result |= 1 << i
    return result


def simhash128(tokens: list[str]) -> tuple[int, int]:
    v = [0] * 128
    for token in tokens:
        raw = token.encode("utf-8")
        h1 = fnv1a64(raw)
        h2 = fnv1a64(raw + b"\xff")
        for i in range(64):
            if (h1 >> i) & 1:
                v[i] += 1
            else:
                v[i] -= 1
            if (h2 >> i) & 1:
                v[64 + i] += 1
            else:
                v[64 + i] -= 1
    lo = 0
    hi = 0
    for i in range(64):
        if v[i] > 0:
            lo |= 1 << i
        if v[64 + i] > 0:
            hi |= 1 << i
    return (hi, lo)


def minhash_params(num_perm: int) -> list[tuple[int, int]]:
    state = LCG_SEED
    params: list[tuple[int, int]] = []
    for _ in range(num_perm):
        state = (state * LCG_MUL + LCG_INC) & MASK64
        a = state % MERSENNE_61
        if a == 0:
            a = 1
        state = (state * LCG_MUL + LCG_INC) & MASK64
        b = state % MERSENNE_61
        params.append((a, b))
    return params


def minhash(tokens: list[str], num_perm: int) -> list[int]:
    if num_perm < 1:
        raise ValueError("[ERR_MINHASH_PERM] num_perm must be > 0")
    params = minhash_params(num_perm)
    signature = [MASK64] * num_perm
    for token in tokens:
        h = fnv1a64(token.encode("utf-8"))
        for i, (a, b) in enumerate(params):
            val = (a * (h % MERSENNE_61) + b) % MERSENNE_61
            if val < signature[i]:
                signature[i] = val
    return signature


def band_hash(band_values: list[int]) -> int:
    h = FNV64_OFFSET
    for val in band_values:
        for byte_idx in range(8):
            byte = (val >> (byte_idx * 8)) & 0xFF
            h ^= byte
            h = (h * FNV64_PRIME) & MASK64
    return h


def lsh_simulate(
    bands: int,
    rows: int,
    inserts: list[tuple[str, list[int]]],
    query_sig: list[int],
    remove: tuple[str, list[int]] | None = None,
) -> tuple[list[str], list[str] | None]:
    """Simulate the LSH contract; returns (query_result, after_remove)."""
    if bands < 1 or rows < 1:
        raise ValueError("[ERR_LSH_CONFIG] bands and rows must be > 0")
    buckets: list[dict[int, list[str]]] = [{} for _ in range(bands)]

    def insert(doc_id: str, sig: list[int]) -> None:
        for b in range(bands):
            key = band_hash(sig[b * rows:(b + 1) * rows])
            buckets[b].setdefault(key, []).append(doc_id)

    def query(sig: list[int]) -> list[str]:
        cand: set[str] = set()
        for b in range(bands):
            key = band_hash(sig[b * rows:(b + 1) * rows])
            cand.update(buckets[b].get(key, ()))
        return sorted(cand)

    for doc_id, sig in inserts:
        insert(doc_id, sig)
    result = query(query_sig)
    if remove is None:
        return result, None
    remove_id, remove_sig = remove
    for b in range(bands):
        key = band_hash(remove_sig[b * rows:(b + 1) * rows])
        if key in buckets[b]:
            buckets[b][key] = [d for d in buckets[b][key] if d != remove_id]
    return result, query(query_sig)


# ---------------------------------------------------------------------------
# Case builders
# ---------------------------------------------------------------------------
FOX = "the quick brown fox jumps over the lazy dog"
CAT = "the quick brown cat jumps over the lazy dog"

SHA256_CASES = [
    ("sha256-empty", "", None),
    ("sha256-hello", "hello", None),
    ("sha256-abc", "abc", None),
    ("sha256-fox", FOX, None),
    ("sha256-fips-896bit", "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq", None),
    ("sha256-utf8-latin", "héllo wörld", None),
    ("sha256-utf8-cjk", "你好，世界", None),
    ("sha256-utf8-emoji", "hi 👋 there", None),
    # Padding boundary cases: 55 (no pad byte after 0x80), 56, 57, 63, 64, 65.
    ("sha256-bytes-55", None, bytes(range(55))),
    ("sha256-bytes-56", None, bytes(range(56))),
    ("sha256-bytes-57", None, bytes(range(57))),
    ("sha256-bytes-63", None, bytes(range(63))),
    ("sha256-bytes-64", None, bytes(range(64))),
    ("sha256-bytes-65", None, bytes(range(65))),
    ("sha256-bytes-0x00-0xff", None, bytes(range(256))),
]


def build_sha256() -> list[dict]:
    out = []
    for case_id, text, raw in SHA256_CASES:
        if text is not None:
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            out.append({"id": case_id, "input": text, "expected_hex": digest})
        else:
            assert raw is not None
            digest = hashlib.sha256(raw).hexdigest()
            out.append({"id": case_id, "input_hex": raw.hex(), "expected_hex": digest})
    return out


FNV_CASES = [
    ("fnv1a-empty", "", None),
    ("fnv1a-hello", "hello", None),
    ("fnv1a-the", "the", None),
    ("fnv1a-fox-sentence", FOX, None),
    ("fnv1a-utf8-latin", "héllo", None),
    ("fnv1a-utf8-cjk", "你好", None),
    ("fnv1a-utf8-emoji", "👋", None),
    ("fnv1a-byte-00", None, b"\x00"),
    ("fnv1a-bytes-000102", None, b"\x00\x01\x02"),
    ("fnv1a-bytes-ff-x8", None, b"\xff" * 8),
]


def build_fnv() -> list[dict]:
    out = []
    for case_id, text, raw in FNV_CASES:
        if text is not None:
            data = text.encode("utf-8")
        else:
            assert raw is not None
            data = raw
        out.append({"id": case_id, "input_hex": data.hex(), "expected_hex": h64(fnv1a64(data))})
    return out


SHINGLE_CASES = [
    ("shingle-char-3", "abcde", "character", 3),
    ("shingle-word-2", FOX, "word", 2),
    ("shingle-char-2-hello", "hello", "character", 2),
    ("shingle-word-3", "a b c d", "word", 3),
    ("shingle-char-1", "abc", "character", 1),
    ("shingle-char-n-gt-len", "ab", "character", 5),
    ("shingle-word-n-gt-len", "a b", "word", 4),
    ("shingle-char-empty", "", "character", 3),
    ("shingle-word-ws-collapse", "a   b\t\tc\n\nc", "word", 2),
    ("shingle-char-utf8-latin", "héllo", "character", 2),
    ("shingle-char-utf8-cjk", "你好世界", "character", 2),
    ("shingle-char-nonbmp-emoji", "hi 👋 yo", "character", 3),
    ("shingle-word-nbsp", "a\u00a0b\u3000c", "word", 2),
    ("shingle-char-n-eq-len", "abcd", "character", 4),
]


def build_shingle() -> list[dict]:
    return [
        {
            "id": cid,
            "input": text,
            "mode": mode,
            "n": n,
            "expected": shingles(text, mode, n),
        }
        for cid, text, mode, n in SHINGLE_CASES
    ]


SIMHASH64_CASES = [
    ("simhash64-fox", FOX),
    ("simhash64-cat", CAT),
    ("simhash64-hello-world", "hello world"),
    ("simhash64-empty", ""),
    ("simhash64-ws-only", "   \t\n\u00a0"),
    ("simhash64-single-a", "a"),
    ("simhash64-repeated", "a a a a"),
    ("simhash64-utf8-latin", "héllo wörld"),
    ("simhash64-utf8-cjk", "你好 世界"),
    ("simhash64-mixed", "Rust, TypeScript, Python, Go, PHP — satu kontrak!"),
]


def build_simhash64() -> list[dict]:
    return [
        {"id": cid, "input": text, "expected_hex": h64(simhash64(tokenize(text)))}
        for cid, text in SIMHASH64_CASES
    ]


SIMHASH128_CASES = [
    ("simhash128-fox", FOX),
    ("simhash128-cat", CAT),
    ("simhash128-hello-world", "hello world"),
    ("simhash128-empty", ""),
    ("simhash128-utf8-cjk", "你好 世界"),
    ("simhash128-utf8-emoji", "hi 👋 there"),
]


def build_simhash128() -> list[dict]:
    out = []
    for cid, text in SIMHASH128_CASES:
        hi, lo = simhash128(tokenize(text))
        out.append({"id": cid, "input": text, "hi_hex": h64(hi), "lo_hex": h64(lo), "hex": h64(hi) + h64(lo)})
    return out


MINHASH_SIG_CASES = [
    ("minhash-sig-fox-128", FOX.split(), 128),
    ("minhash-sig-hello-world-64", ["hello", "world"], 64),
    ("minhash-sig-abcd-100", ["a", "b", "c", "d"], 100),
    ("minhash-sig-single-8", ["x"], 8),
    ("minhash-sig-empty-8", [], 8),
    ("minhash-sig-unicode-32", ["你好", "世界"], 32),
    ("minhash-sig-duplicates-16", ["a", "a", "b"], 16),
]


def build_minhash_sig() -> list[dict]:
    out = []
    for cid, tokens, num_perm in MINHASH_SIG_CASES:
        sig = minhash(tokens, num_perm)
        out.append({
            "id": cid,
            "tokens": tokens,
            "num_perm": num_perm,
            "signature_hex": [h64(v) for v in sig],
        })
    return out


def build_minhash_jaccard() -> list[dict]:
    out = []
    pairs = [
        ("minhash-jaccard-identical", FOX.split(), FOX.split(), 128),
        ("minhash-jaccard-fox-vs-hello", FOX.split(), ["hello", "world"], 128),
        ("minhash-jaccard-overlap", ["a", "b", "c", "d"], ["c", "d", "e", "f"], 128),
        ("minhash-jaccard-disjoint", ["alpha", "beta", "gamma"], ["delta", "epsilon", "zeta"], 64),
    ]
    for cid, set_a, set_b, num_perm in pairs:
        sig_a = minhash(set_a, num_perm)
        sig_b = minhash(set_b, num_perm)
        matches = sum(1 for x, y in zip(sig_a, sig_b) if x == y)
        out.append({
            "id": cid,
            "set_a": set_a,
            "set_b": set_b,
            "num_perm": num_perm,
            "expected_matches": matches,
        })
    return out


def build_lsh_bandhash() -> list[dict]:
    fox_sig = minhash(FOX.split(), 100)
    cases = [
        ("lsh-bandhash-fox-100-first-band", fox_sig[0:5]),
        ("lsh-bandhash-zeros", [0, 0, 0]),
        ("lsh-bandhash-max", [MASK64, MASK64]),
        ("lsh-bandhash-mixed", [0, MASK64, 1]),
        ("lsh-bandhash-single", [1]),
    ]
    return [
        {
            "id": cid,
            "band_values_hex": [h64(v) for v in vals],
            "expected_key_hex": h64(band_hash(vals)),
        }
        for cid, vals in cases
    ]


def build_lsh_index() -> list[dict]:
    sig4_abcd = minhash(["a", "b", "c", "d"], 4)
    sig4_cdef = minhash(["c", "d", "e", "f"], 4)
    fox_sig100 = minhash(FOX.split(), 100)
    hello_sig100 = minhash(["hello", "world"], 100)
    uni_sig = minhash(["你好", "世界", "alpha"], 6)

    inserts_and_queries = [
        {
            "id": "lsh-index-2x2",
            "bands": 2,
            "rows": 2,
            "inserts": [
                {"doc_id": "doc1", "signature_hex": [h64(v) for v in sig4_abcd]},
                {"doc_id": "doc2", "signature_hex": [h64(v) for v in sig4_cdef]},
            ],
            "query_hex": [h64(v) for v in sig4_abcd],
            "remove": {"doc_id": "doc1", "signature_hex": [h64(v) for v in sig4_abcd]},
        },
        {
            "id": "lsh-index-20x5-fox",
            "bands": 20,
            "rows": 5,
            "inserts": [
                {"doc_id": "doc1", "signature_hex": [h64(v) for v in fox_sig100]},
                {"doc_id": "doc2", "signature_hex": [h64(v) for v in hello_sig100]},
            ],
            "query_hex": [h64(v) for v in fox_sig100],
        },
        {
            "id": "lsh-index-dup-ids",
            "bands": 3,
            "rows": 1,
            "inserts": [
                {"doc_id": "b_doc", "signature_hex": [h64(v) for v in uni_sig]},
                {"doc_id": "a_doc", "signature_hex": [h64(v) for v in uni_sig]},
                {"doc_id": "c_doc", "signature_hex": [h64(v) for v in uni_sig]},
                {"doc_id": "a_doc", "signature_hex": [h64(v) for v in uni_sig]},
            ],
            "query_hex": [h64(v) for v in uni_sig],
        },
        {
            "id": "lsh-index-unicode-ids",
            "bands": 2,
            "rows": 3,
            "inserts": [
                {"doc_id": "doc-你好", "signature_hex": [h64(v) for v in uni_sig]},
                {"doc_id": "doc-alpha", "signature_hex": [h64(v) for v in sig4_cdef + sig4_abcd[:2]]},
            ],
            "query_hex": [h64(v) for v in uni_sig],
        },
    ]

    out = []
    for case in inserts_and_queries:
        inserts = [(d["doc_id"], [int(v, 16) for v in d["signature_hex"]]) for d in case["inserts"]]
        query_sig = [int(v, 16) for v in case["query_hex"]]
        remove = None
        if "remove" in case:
            remove = (
                case["remove"]["doc_id"],
                [int(v, 16) for v in case["remove"]["signature_hex"]],
            )
        result, after = lsh_simulate(case["bands"], case["rows"], inserts, query_sig, remove)
        case["expected"] = result
        if after is not None:
            case["expected_after_remove"] = after
        out.append(case)
    return out


# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------
def build_document() -> dict:
    return {
        "schema": "lomboksimhash-vectors-v2",
        "generator": "vectors/generate_vectors.py",
        "description": (
            "Deterministic cross-language test vectors. Generated by the "
            "script; never hand-edited. All ports consume this exact file."
        ),
        "constants": {
            "fnv64_offset": "0xcbf29ce484222325",
            "fnv64_prime": "0x100000001b3",
            "lcg_seed": "0x517cc1b727220a95",
            "lcg_multiplier": "6364136223846793005",
            "lcg_increment": "1442695040888963407",
            "mersenne_61": "2305843009213693951",
            "mask64": "18446744073709551615",
        },
        "cases": {
            "sha256": build_sha256(),
            "fnv1a64": build_fnv(),
            "shingle": build_shingle(),
            "simhash64": build_simhash64(),
            "simhash128": build_simhash128(),
            "minhash_signature": build_minhash_sig(),
            "minhash_jaccard": build_minhash_jaccard(),
            "lsh_bandhash": build_lsh_bandhash(),
            "lsh_index": build_lsh_index(),
        },
    }


def render(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    doc = build_document()
    text = render(doc)
    if "--check" in sys.argv:
        if not OUT.exists():
            print(f"FAIL: {OUT.name} does not exist")
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print("FAIL: regenerated vectors differ from committed file")
            return 1
        print(f"OK: {OUT.name} reproduces byte-identically")
        return 0
    OUT.write_text(text, encoding="utf-8")
    total = sum(len(v) for v in doc["cases"].values())
    file_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"wrote {OUT.name}: {total} cases, sha256={file_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
