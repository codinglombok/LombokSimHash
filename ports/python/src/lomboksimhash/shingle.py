"""Shingling — character/word n-gram generation (streaming).

Behavior pinned by docs/SPEC_LombokSimHash_0.1.0.md.
"""

from __future__ import annotations

from ._core import tokenize

_SHINGLE_N_MSG = "[ERR_SHINGLE_N] shingle size must be > 0"


def _assert_n(n: int) -> None:
    if n < 1:
        raise ValueError(_SHINGLE_N_MSG)


class Shingler:
    """Streaming shingle generator.

    Character mode slices Unicode code points; word mode slices tokens
    produced by the SPEC tokenizer and joins them with a single U+0020.
    finish() returns unique shingles sorted by code point.
    """

    __slots__ = ("_mode", "_n", "_buffer")

    def __init__(self, mode: str = "character", n: int = 3) -> None:
        _assert_n(n)
        if mode not in ("character", "word"):
            raise ValueError("mode must be 'character' or 'word'")
        self._mode = mode
        self._n = n
        self._buffer = ""

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def n(self) -> int:
        return self._n

    def feed(self, text: str) -> None:
        self._buffer += text

    def finish(self) -> list[str]:
        """Return sorted unique shingles."""
        if self._mode == "character":
            chars = list(self._buffer)
            count = len(chars)
            return sorted(
                {"".join(chars[i:i + self._n]) for i in range(count - self._n + 1)}
            )
        words = tokenize(self._buffer)
        count = len(words)
        return sorted(
            {" ".join(words[i:i + self._n]) for i in range(count - self._n + 1)}
        )

    def feed_finish(self, text: str) -> list[str]:
        """Convenience: feed(text) then finish()."""
        self.feed(text)
        return self.finish()


def char_shingles(text: str, n: int) -> list[str]:
    """Convenience: sorted unique character n-grams (code points)."""
    _assert_n(n)
    return Shingler("character", n).feed_finish(text)


def word_shingles(text: str, n: int) -> list[str]:
    """Convenience: sorted unique word n-grams."""
    _assert_n(n)
    return Shingler("word", n).feed_finish(text)
