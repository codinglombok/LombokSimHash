"""
LombokSimHash — Python Port
Near-duplicate document detection for RAG pipelines.
Zero dependencies, pure Python.

Features:
- SHA-256 (FIPS 180-4)
- FNV-1a 64-bit
- SimHash 64/128-bit
- MinHash with Jaccard estimation
- LSH (Locality-Sensitive Hashing)
- Shingling (character/word n-grams)

Part of LombokRAGFrameworks.
License: Apache-2.0
"""

import struct
from typing import List, Set, Tuple, Dict, Optional

__version__ = "0.1.0"
__all__ = [
    "sha256", "fnv1a64",
    "Shingler",
    "simhash64", "simhash64_text", "simhash128", "simhash128_text",
    "hamming64", "hamming128",
    "MinHasher", "jaccard_estimate",
    "LshIndex",
]

# ============================================================
# SHA-256 (FIPS 180-4)
# ============================================================

_K_SHA = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

_H_INIT = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]

_MASK32 = 0xFFFFFFFF


def _rotr32(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & _MASK32


def _sha256_compress(state: List[int], block: bytes) -> None:
    w = [0] * 64
    for i in range(16):
        w[i] = struct.unpack(">I", block[i*4:i*4+4])[0]
    for i in range(16, 64):
        s0 = _rotr32(w[i-15], 7) ^ _rotr32(w[i-15], 18) ^ (w[i-15] >> 3)
        s1 = _rotr32(w[i-2], 17) ^ _rotr32(w[i-2], 19) ^ (w[i-2] >> 10)
        w[i] = (w[i-16] + s0 + w[i-7] + s1) & _MASK32

    a, b, c, d, e, f, g, h = state

    for i in range(64):
        s1 = _rotr32(e, 6) ^ _rotr32(e, 11) ^ _rotr32(e, 25)
        ch = (e & f) ^ ((~e & _MASK32) & g)
        temp1 = (h + s1 + ch + _K_SHA[i] + w[i]) & _MASK32
        s0 = _rotr32(a, 2) ^ _rotr32(a, 13) ^ _rotr32(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        temp2 = (s0 + maj) & _MASK32

        h = g
        g = f
        f = e
        e = (d + temp1) & _MASK32
        d = c
        c = b
        b = a
        a = (temp1 + temp2) & _MASK32

    for i, v in enumerate([a, b, c, d, e, f, g, h]):
        state[i] = (state[i] + v) & _MASK32


def sha256(data: bytes | str) -> str:
    """Compute SHA-256 hash. Returns hex string."""
    if isinstance(data, str):
        data = data.encode("utf-8")

    state = list(_H_INIT)
    bit_len = len(data) * 8

    padded = bytearray(data)
    padded.append(0x80)
    while len(padded) % 64 != 56:
        padded.append(0x00)
    padded.extend(bit_len.to_bytes(8, "big"))

    for i in range(0, len(padded), 64):
        _sha256_compress(state, bytes(padded[i:i+64]))

    return "".join(f"{v:08x}" for v in state)


# ============================================================
# FNV-1a 64-bit
# ============================================================

_FNV64_OFFSET = 0xCBF29CE484222325
_FNV64_PRIME = 0x100000001B3
_MASK64 = (1 << 64) - 1


def fnv1a64(data: bytes) -> int:
    """FNV-1a 64-bit hash."""
    h = _FNV64_OFFSET
    for b in data:
        h ^= b
        h = (h * _FNV64_PRIME) & _MASK64
    return h


# ============================================================
# Shingling
# ============================================================

class Shingler:
    """Streaming shingle generator."""

    def __init__(self, mode: str = "character", n: int = 3):
        assert n > 0, "shingle size must be > 0"
        self.mode = mode
        self.n = n
        self._buffer = ""

    def feed(self, text: str) -> None:
        self._buffer += text

    def finish(self) -> List[str]:
        """Return sorted unique shingles."""
        result: Set[str] = set()
        if self.mode == "character":
            chars = list(self._buffer)
            for i in range(len(chars) - self.n + 1):
                result.add("".join(chars[i:i+self.n]))
        else:
            words = self._buffer.split()
            for i in range(len(words) - self.n + 1):
                result.add(" ".join(words[i:i+self.n]))
        return sorted(result)


# ============================================================
# SimHash
# ============================================================

def simhash64(tokens: List[str]) -> int:
    """Compute 64-bit SimHash from token list."""
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


def simhash64_text(text: str) -> int:
    """Tokenize by whitespace and compute simhash64."""
    return simhash64(text.split())


def simhash128(tokens: List[str]) -> Tuple[int, int]:
    """Compute 128-bit SimHash. Returns (high, low)."""
    v = [0] * 128
    for token in tokens:
        h1 = fnv1a64(token.encode("utf-8"))
        h2 = fnv1a64(token.encode("utf-8") + b"\xff")
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


def simhash128_text(text: str) -> Tuple[int, int]:
    """Tokenize by whitespace and compute simhash128."""
    return simhash128(text.split())


def hamming64(a: int, b: int) -> int:
    """Hamming distance between two 64-bit values."""
    return bin(a ^ b).count("1")


def hamming128(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Hamming distance between two 128-bit values."""
    return bin(a[0] ^ b[0]).count("1") + bin(a[1] ^ b[1]).count("1")


# ============================================================
# MinHash
# ============================================================

_MERSENNE_61 = (1 << 61) - 1
_LCG_SEED = 0x517CC1B727220A95
_LCG_MUL = 6364136223846793005
_LCG_INC = 1442695040888963407


def _generate_hash_params(num_perm: int) -> List[Tuple[int, int]]:
    state = _LCG_SEED
    params = []
    for _ in range(num_perm):
        state = (state * _LCG_MUL + _LCG_INC) & _MASK64
        a = max(1, state % _MERSENNE_61)
        state = (state * _LCG_MUL + _LCG_INC) & _MASK64
        b = state % _MERSENNE_61
        params.append((a, b))
    return params


def _universal_hash(a: int, b: int, x: int) -> int:
    return (a * (x % _MERSENNE_61) + b) % _MERSENNE_61


class MinHasher:
    """MinHash signature generator."""

    def __init__(self, num_perm: int = 128):
        self.num_perm = num_perm
        self._params = _generate_hash_params(num_perm)
        self.signature = [_MASK64] * num_perm

    def add(self, token: str) -> None:
        h = fnv1a64(token.encode("utf-8"))
        for i in range(self.num_perm):
            a, b = self._params[i]
            val = _universal_hash(a, b, h)
            if val < self.signature[i]:
                self.signature[i] = val

    def add_tokens(self, tokens: List[str]) -> None:
        for t in tokens:
            self.add(t)


def jaccard_estimate(sig_a: List[int], sig_b: List[int]) -> float:
    """Estimate Jaccard similarity from MinHash signatures."""
    assert len(sig_a) == len(sig_b), "signatures must have same length"
    matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
    return matches / len(sig_a)


# ============================================================
# LSH Index
# ============================================================

class LshIndex:
    """LSH index using band+row technique over MinHash signatures."""

    def __init__(self, bands: int, rows: int):
        self.bands = bands
        self.rows = rows
        self._buckets: List[Dict[int, List[str]]] = [{} for _ in range(bands)]

    @property
    def signature_len(self) -> int:
        return self.bands * self.rows

    def threshold(self) -> float:
        return (1.0 / self.bands) ** (1.0 / self.rows)

    @staticmethod
    def _band_hash(band_values: List[int]) -> int:
        h = _FNV64_OFFSET
        for val in band_values:
            for byte_idx in range(8):
                byte = (val >> (byte_idx * 8)) & 0xFF
                h ^= byte
                h = (h * _FNV64_PRIME) & _MASK64
        return h

    def insert(self, doc_id: str, signature: List[int]) -> None:
        assert len(signature) == self.signature_len
        for b in range(self.bands):
            start = b * self.rows
            band_vals = signature[start:start + self.rows]
            key = self._band_hash(band_vals)
            self._buckets[b].setdefault(key, []).append(doc_id)

    def query(self, signature: List[int]) -> List[str]:
        assert len(signature) == self.signature_len
        candidates: Set[str] = set()
        for b in range(self.bands):
            start = b * self.rows
            band_vals = signature[start:start + self.rows]
            key = self._band_hash(band_vals)
            bucket = self._buckets[b].get(key, [])
            candidates.update(bucket)
        return sorted(candidates)

    def remove(self, doc_id: str, signature: List[int]) -> None:
        assert len(signature) == self.signature_len
        for b in range(self.bands):
            start = b * self.rows
            band_vals = signature[start:start + self.rows]
            key = self._band_hash(band_vals)
            if key in self._buckets[b]:
                self._buckets[b][key] = [
                    d for d in self._buckets[b][key] if d != doc_id
                ]
