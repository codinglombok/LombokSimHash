"""FNV-1a 64-bit and shared helpers (tokenization, hex formatting).

Behavior pinned by docs/SPEC_LombokSimHash_0.1.0.md.
"""

from __future__ import annotations

FNV64_OFFSET = 0xCBF29CE484222325
FNV64_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1

# SPEC whitespace set = Unicode White_Space property (exact, cross-language).
WHITESPACE = frozenset(
    "\t\n\x0b\x0c\r \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005"
    "\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
)


def fnv1a64(data: bytes) -> int:
    """FNV-1a 64-bit hash. offset 0xcbf29ce484222325, prime 0x100000001b3."""
    h = FNV64_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV64_PRIME) & MASK64
    return h


def to_hex64(value: int) -> str:
    """Format a u64 as 16 lowercase hex chars."""
    return f"{value:016x}"


def tokenize(text: str) -> list[str]:
    """Split text on runs of the SPEC whitespace set; drop empty parts."""
    return [t for t in _split_ws(text) if t]


def _split_ws(text: str) -> list[str]:
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
