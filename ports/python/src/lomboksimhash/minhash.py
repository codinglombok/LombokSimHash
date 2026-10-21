"""MinHash — Jaccard estimation via deterministic k-permutation family.

Behavior pinned by docs/SPEC_LombokSimHash_0.1.0.md.
"""

from __future__ import annotations

from typing import Sequence

from ._core import MASK64, fnv1a64

MERSENNE_61 = (1 << 61) - 1
LCG_SEED = 0x517CC1B727220A95
LCG_MUL = 6364136223846793005
LCG_INC = 1442695040888963407


def _assert_num_perm(num_perm: int) -> None:
    if num_perm < 1:
        raise ValueError("[ERR_MINHASH_PERM] num_perm must be > 0")


def _generate_hash_params(num_perm: int) -> list[tuple[int, int]]:
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


def _universal_hash(a: int, b: int, x: int) -> int:
    return (a * (x % MERSENNE_61) + b) % MERSENNE_61


class MinHasher:
    """MinHash signature generator with a deterministic permutation family."""

    __slots__ = ("_num_perm", "_params", "signature")

    def __init__(self, num_perm: int = 128) -> None:
        _assert_num_perm(num_perm)
        self._num_perm = num_perm
        self._params = _generate_hash_params(num_perm)
        self.signature = [MASK64] * num_perm

    @property
    def num_perm(self) -> int:
        return self._num_perm

    def add(self, token: str) -> None:
        """Fold one token into the signature."""
        h = fnv1a64(token.encode("utf-8"))
        for i in range(self._num_perm):
            a, b = self._params[i]
            val = _universal_hash(a, b, h)
            if val < self.signature[i]:
                self.signature[i] = val

    def add_tokens(self, tokens: Sequence[str]) -> None:
        """Fold a sequence of tokens into the signature (order-independent)."""
        for t in tokens:
            self.add(t)


def jaccard_estimate(sig_a: Sequence[int], sig_b: Sequence[int]) -> float:
    """Estimated Jaccard = matched positions / signature length."""
    if len(sig_a) != len(sig_b):
        raise ValueError("[ERR_JACCARD_LEN] signatures must have same length")
    if len(sig_a) == 0:
        raise ValueError("[ERR_JACCARD_EMPTY] signatures must not be empty")
    matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
    return matches / len(sig_a)
