"""LSH — band+row locality-sensitive hashing over MinHash signatures.

Behavior pinned by docs/SPEC_LombokSimHash_0.1.0.md.
"""

from __future__ import annotations

from collections.abc import Sequence

from ._core import FNV64_OFFSET, FNV64_PRIME, MASK64


def _assert_config(bands: int, rows: int) -> None:
    if bands < 1 or rows < 1:
        raise ValueError("[ERR_LSH_CONFIG] bands and rows must be > 0")


def _assert_sig_len(signature: Sequence[int], expected: int) -> None:
    if len(signature) != expected:
        raise ValueError(
            f"[ERR_SIG_LEN] signature length must be bands * rows = {expected}"
        )


def band_hash(band_values: Sequence[int]) -> int:
    """FNV-1a 64 over the little-endian bytes of each u64 in the band."""
    h = FNV64_OFFSET
    for val in band_values:
        for byte_idx in range(8):
            byte = (val >> (byte_idx * 8)) & 0xFF
            h ^= byte
            h = (h * FNV64_PRIME) & MASK64
    return h


class LshIndex:
    """LSH index (band+row) over MinHash signatures.

    query() returns de-duplicated doc IDs sorted ascending by code point.
    """

    __slots__ = ("_bands", "_rows", "_buckets")

    def __init__(self, bands: int, rows: int) -> None:
        _assert_config(bands, rows)
        self._bands = bands
        self._rows = rows
        self._buckets: list[dict[int, list[str]]] = [{} for _ in range(bands)]

    @property
    def bands(self) -> int:
        return self._bands

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def signature_len(self) -> int:
        return self._bands * self._rows

    def threshold(self) -> float:
        """Approximate Jaccard threshold (1/bands)^(1/rows). Informational."""
        base = 1.0 / self._bands
        expo = 1.0 / self._rows
        return float(base ** expo)

    def insert(self, doc_id: str, signature: Sequence[int]) -> None:
        """Insert a document signature into every band."""
        _assert_sig_len(signature, self.signature_len)
        for b in range(self._bands):
            start = b * self._rows
            key = band_hash(signature[start:start + self._rows])
            self._buckets[b].setdefault(key, []).append(doc_id)

    def query(self, signature: Sequence[int]) -> list[str]:
        """Return sorted unique candidate doc IDs for the signature."""
        _assert_sig_len(signature, self.signature_len)
        candidates: set[str] = set()
        for b in range(self._bands):
            start = b * self._rows
            key = band_hash(signature[start:start + self._rows])
            candidates.update(self._buckets[b].get(key, ()))
        return sorted(candidates)

    def remove(self, doc_id: str, signature: Sequence[int]) -> None:
        """Remove a doc ID from every band bucket touched by the signature."""
        _assert_sig_len(signature, self.signature_len)
        for b in range(self._bands):
            start = b * self._rows
            key = band_hash(signature[start:start + self._rows])
            if key in self._buckets[b]:
                self._buckets[b][key] = [
                    d for d in self._buckets[b][key] if d != doc_id
                ]
