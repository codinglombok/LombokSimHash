"""Vector tests — consume the ONE shared cross-language vectors file."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from lomboksimhash import (
    LshIndex,
    MinHasher,
    band_hash,
    char_shingles,
    fnv1a64,
    jaccard_estimate,
    sha256,
    simhash64_text,
    simhash128_text,
    word_shingles,
)

VECTORS = (
    Path(__file__).resolve().parents[3] / "vectors" / "lomboksimhash-vectors-v2.json"
)


@pytest.fixture(scope="module")
def doc() -> dict[str, Any]:
    with VECTORS.open(encoding="utf-8") as f:
        data = json.load(f)
    assert data["schema"] == "lomboksimhash-vectors-v2"
    return data


def hex64(v: int) -> str:
    return f"{v:016x}"


def sig_of(hexes: list[str]) -> list[int]:
    return [int(h, 16) for h in hexes]


def test_sha256_vectors(doc: dict[str, Any]) -> None:
    for case in doc["cases"]["sha256"]:
        data = case.get("input")
        raw = data.encode("utf-8") if isinstance(data, str) else bytes.fromhex(case["input_hex"])
        assert sha256(raw) == case["expected_hex"], f"case {case['id']}"


def test_fnv_vectors(doc: dict[str, Any]) -> None:
    for case in doc["cases"]["fnv1a64"]:
        got = hex64(fnv1a64(bytes.fromhex(case["input_hex"])))
        assert got == case["expected_hex"], f"case {case['id']}"


def test_shingle_vectors(doc: dict[str, Any]) -> None:
    for case in doc["cases"]["shingle"]:
        fn = char_shingles if case["mode"] == "character" else word_shingles
        got = fn(case["input"], case["n"])
        assert got == case["expected"], f"case {case['id']}"


def test_simhash64_vectors(doc: dict[str, Any]) -> None:
    for case in doc["cases"]["simhash64"]:
        got = hex64(simhash64_text(case["input"]))
        assert got == case["expected_hex"], f"case {case['id']}"


def test_simhash128_vectors(doc: dict[str, Any]) -> None:
    for case in doc["cases"]["simhash128"]:
        hi, lo = simhash128_text(case["input"])
        assert hex64(hi) == case["hi_hex"], f"case {case['id']} hi"
        assert hex64(lo) == case["lo_hex"], f"case {case['id']} lo"
        assert hex64(hi) + hex64(lo) == case["hex"], f"case {case['id']} hex"


def test_minhash_signature_vectors(doc: dict[str, Any]) -> None:
    for case in doc["cases"]["minhash_signature"]:
        mh = MinHasher(case["num_perm"])
        mh.add_tokens(case["tokens"])
        got = [hex64(v) for v in mh.signature]
        assert got == case["signature_hex"], f"case {case['id']}"


def test_minhash_jaccard_vectors(doc: dict[str, Any]) -> None:
    for case in doc["cases"]["minhash_jaccard"]:
        num_perm = case["num_perm"]
        a = MinHasher(num_perm)
        b = MinHasher(num_perm)
        a.add_tokens(case["set_a"])
        b.add_tokens(case["set_b"])
        matches = sum(1 for x, y in zip(a.signature, b.signature, strict=False) if x == y)
        assert matches == case["expected_matches"], f"case {case['id']}"
        assert jaccard_estimate(a.signature, b.signature) == matches / num_perm


def test_lsh_bandhash_vectors(doc: dict[str, Any]) -> None:
    for case in doc["cases"]["lsh_bandhash"]:
        values = sig_of(case["band_values_hex"])
        got = hex64(band_hash(values))
        assert got == case["expected_key_hex"], f"case {case['id']}"
        idx = LshIndex(1, len(values))
        idx.insert("probe", values)
        assert "probe" in idx.query(values)


def test_lsh_index_vectors(doc: dict[str, Any]) -> None:
    for case in doc["cases"]["lsh_index"]:
        idx = LshIndex(case["bands"], case["rows"])
        for ins in case["inserts"]:
            idx.insert(ins["doc_id"], sig_of(ins["signature_hex"]))
        got = idx.query(sig_of(case["query_hex"]))
        assert got == case["expected"], f"case {case['id']}"
        remove = case.get("remove")
        if remove:
            idx.remove(remove["doc_id"], sig_of(remove["signature_hex"]))
            after = idx.query(sig_of(case["query_hex"]))
            assert after == case["expected_after_remove"], f"case {case['id']}"


def test_vector_file_deterministic(doc: dict[str, Any]) -> None:
    # The committed file must equal a fresh regeneration (spec §7).
    repo = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, str(repo / "vectors" / "generate_vectors.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
