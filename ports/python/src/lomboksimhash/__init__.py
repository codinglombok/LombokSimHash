"""LombokSimHash — Python Port.

Near-duplicate document detection for RAG pipelines:
SHA-256, FNV-1a 64, SimHash 64/128, MinHash, LSH, shingling.

Zero dependencies. Behavior pinned by docs/SPEC_LombokSimHash_0.1.0.md;
all ports are validated against vectors/lomboksimhash-vectors-v2.json.

Part of LombokRAGFrameworks (Lombok Ecosystem).
License: Apache-2.0
"""

from __future__ import annotations

from ._core import FNV64_OFFSET, FNV64_PRIME, MASK64, WHITESPACE, fnv1a64, to_hex64, tokenize
from ._lsh import LshIndex, band_hash
from ._minhash import MinHasher, jaccard_estimate
from ._sha256 import Sha256State, sha256, to_hex
from ._shingle import Shingler, char_shingles, word_shingles
from ._simhash import hamming64, hamming128, simhash64, simhash64_text, simhash128, simhash128_text

__version__ = "0.1.0"

__all__ = [
    "MASK64",
    "FNV64_OFFSET",
    "FNV64_PRIME",
    "WHITESPACE",
    "Sha256State",
    "LshIndex",
    "MinHasher",
    "Shingler",
    "band_hash",
    "char_shingles",
    "word_shingles",
    "fnv1a64",
    "hamming128",
    "hamming64",
    "jaccard_estimate",
    "sha256",
    "simhash128",
    "simhash128_text",
    "simhash64",
    "simhash64_text",
    "to_hex",
    "to_hex64",
    "tokenize",
]
