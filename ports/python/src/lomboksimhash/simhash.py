"""SimHash — 64/128-bit locality-sensitive fingerprinting via FNV-1a.

Behavior pinned by docs/SPEC_LombokSimHash_0.1.0.md.
"""

from __future__ import annotations

from typing import Sequence

from ._core import fnv1a64, tokenize


def simhash64(tokens: Sequence[str]) -> int:
    """64-bit SimHash over token list. Bit i set iff weight[i] > 0 (LSB first)."""
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
    """Tokenize by the SPEC whitespace set, then simhash64."""
    return simhash64(tokenize(text))


def simhash128(tokens: Sequence[str]) -> tuple[int, int]:
    """128-bit SimHash. Returns (hi, lo).

    lo = simhash of fnv1a64(utf8(token)); hi = simhash of
    fnv1a64(utf8(token) || 0xFF).
    """
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


def simhash128_text(text: str) -> tuple[int, int]:
    """Tokenize by the SPEC whitespace set, then simhash128."""
    return simhash128(tokenize(text))


def hamming64(a: int, b: int) -> int:
    """Hamming distance between two 64-bit values."""
    return bin(a ^ b).count("1")


def hamming128(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Hamming distance between two 128-bit (hi, lo) pairs."""
    return bin(a[0] ^ b[0]).count("1") + bin(a[1] ^ b[1]).count("1")
