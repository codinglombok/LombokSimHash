"""Unit + API tests for the Python port (error contract, edge cases)."""

from __future__ import annotations

import pytest

from lomboksimhash import (
    LshIndex,
    MinHasher,
    Shingler,
    char_shingles,
    fnv1a64,
    hamming64,
    hamming128,
    jaccard_estimate,
    sha256,
    simhash64,
    simhash64_text,
    simhash128,
    simhash128_text,
    tokenize,
    word_shingles,
)
from lomboksimhash._core import to_hex64
from lomboksimhash._sha256 import Sha256State, to_hex
from lomboksimhash._sha256 import sha256 as sha256_fn

FOX = "the quick brown fox jumps over the lazy dog"


class TestSha256:
    def test_reference_digests(self) -> None:
        assert sha256(b"") == (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        assert sha256("abc") == (
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )

    def test_str_and_bytes_identical(self) -> None:
        assert sha256("héllo") == sha256("héllo".encode())


class TestFnv:
    def test_offset(self) -> None:
        assert fnv1a64(b"") == 0xCBF29CE484222325

    def test_known(self) -> None:
        assert f"{fnv1a64(b'hello'):016x}" == "a430d84680aabd0b"


class TestTokenize:
    def test_spec_whitespace(self) -> None:
        assert tokenize("a\u00a0b\u3000c\u000bd") == ["a", "b", "c", "d"]

    def test_excludes_zwsp_and_bom(self) -> None:
        assert tokenize("a\u200bb") == ["a\u200bb"]
        assert tokenize("a\ufeffb") == ["a\ufeffb"]

    def test_empty(self) -> None:
        assert tokenize("") == []
        assert tokenize(" \t\n") == []


class TestShingling:
    def test_char_and_word(self) -> None:
        assert char_shingles("abcde", 3) == ["abc", "bcd", "cde"]
        assert word_shingles("a   b\t\tc\n\nc", 2) == ["a b", "b c", "c c"]

    def test_streaming_pure(self) -> None:
        s = Shingler("character", 3)
        s.feed("abc")
        s.feed("de")
        assert s.finish() == ["abc", "bcd", "cde"]
        assert s.finish() == ["abc", "bcd", "cde"]  # finish() idempotent

    def test_n_exceeds_len(self) -> None:
        assert char_shingles("ab", 5) == []
        assert word_shingles("a b", 4) == []

    def test_err_shingle_n(self) -> None:
        with pytest.raises(ValueError, match=r"^\[ERR_SHINGLE_N\] shingle size must be > 0$"):
            Shingler("character", 0)
        with pytest.raises(ValueError, match=r"^\[ERR_SHINGLE_N\]"):
            char_shingles("abc", 0)
        with pytest.raises(ValueError, match=r"^\[ERR_SHINGLE_N\]"):
            word_shingles("abc", 0)

    def test_bad_mode(self) -> None:
        with pytest.raises(ValueError, match="mode"):
            Shingler("bogus", 2)


class TestSimhash:
    def test_known(self) -> None:
        assert f"{simhash64_text(FOX):016x}" == "cab7991c5475edee"
        assert f"{simhash64_text(FOX.replace('fox', 'cat')):016x}" == "c2e7991c1465e56f"

    def test_empty(self) -> None:
        assert simhash64([]) == 0
        assert simhash64_text("   \t\n") == 0
        assert simhash128([]) == (0, 0)

    def test_hamming(self) -> None:
        fox = simhash64_text(FOX)
        cat = simhash64_text(FOX.replace("fox", "cat"))
        assert hamming64(fox, cat) == 8
        assert hamming64(fox, fox) == 0

    def test_128_lo_equals_64(self) -> None:
        hi, lo = simhash128_text(FOX)
        assert lo == simhash64_text(FOX)
        assert hi >= 0 and hi < (1 << 64)
        assert hamming128((hi, lo), (hi, lo)) == 0


class TestMinHash:
    def test_identical(self) -> None:
        a = MinHasher(128)
        b = MinHasher(128)
        a.add_tokens(["the", "quick", "brown", "fox"])
        b.add_tokens(["the", "quick", "brown", "fox"])
        assert jaccard_estimate(a.signature, b.signature) == 1.0

    def test_order_independent_and_idempotent(self) -> None:
        a = MinHasher(64)
        b = MinHasher(64)
        a.add_tokens(["hello", "world"])
        b.add_tokens(["world", "hello", "hello"])
        assert a.signature == b.signature

    def test_errors(self) -> None:
        with pytest.raises(ValueError, match=r"^\[ERR_MINHASH_PERM\] num_perm must be > 0$"):
            MinHasher(0)
        a = MinHasher(8)
        b = MinHasher(16)
        with pytest.raises(ValueError, match=r"^\[ERR_JACCARD_LEN\]"):
            jaccard_estimate(a.signature, b.signature)
        with pytest.raises(ValueError, match=r"^\[ERR_JACCARD_EMPTY\]"):
            jaccard_estimate([], [])


class TestLsh:
    def test_errors(self) -> None:
        with pytest.raises(ValueError, match=r"^\[ERR_LSH_CONFIG\]"):
            LshIndex(0, 5)
        with pytest.raises(ValueError, match=r"^\[ERR_LSH_CONFIG\]"):
            LshIndex(20, 0)
        idx = LshIndex(5, 2)
        expected = r"^\[ERR_SIG_LEN\] signature length must be bands \* rows = 10$"
        with pytest.raises(ValueError, match=expected):
            idx.insert("d", [1, 2, 3])
        with pytest.raises(ValueError, match=r"^\[ERR_SIG_LEN\]"):
            idx.query([1])

    def test_sorted_query_and_remove(self) -> None:
        idx = LshIndex(3, 1)
        sig = [1, 2, 3]
        for doc in ("b_doc", "a_doc", "c_doc", "a_doc"):
            idx.insert(doc, sig)
        assert idx.query(sig) == ["a_doc", "b_doc", "c_doc"]
        idx.remove("a_doc", sig)
        assert idx.query(sig) == ["b_doc", "c_doc"]

    def test_threshold(self) -> None:
        assert abs(LshIndex(20, 5).threshold() - 0.5493) < 0.01
        assert LshIndex(1, 1).threshold() == 1.0


class TestSha256State:
    def test_streaming_equals_one_shot(self) -> None:
        data = "Rust TypeScript Python Go PHP — satu kontrak bit-identical 🌍".encode()
        for split in (0, 1, 31, 55, 56, 57, len(data)):
            st = Sha256State()
            st.update(data[:split])
            st.update(data[split:])
            assert st.hexdigest() == sha256_fn(data), f"split {split}"

    def test_digest_non_destructive(self) -> None:
        st = Sha256State()
        st.update(b"hello")
        first = st.digest()
        assert st.digest() == first  # digest() does not destroy state
        st.update(b" world")
        assert st.hexdigest() == sha256_fn(b"hello world")

    def test_finalize_and_to_hex(self) -> None:
        st = Sha256State()
        st.update(b"abc")
        digest = st.finalize()
        assert to_hex(digest) == sha256_fn(b"abc")
        assert len(digest) == 32


class TestAccessors:
    def test_shingler_accessors(self) -> None:
        s = Shingler("word", 4)
        assert s.mode == "word"
        assert s.n == 4

    def test_lsh_accessors(self) -> None:
        idx = LshIndex(7, 3)
        assert idx.bands == 7
        assert idx.rows == 3
        assert idx.signature_len == 21

    def test_to_hex64(self) -> None:
        assert to_hex64(0) == "0" * 16
        assert to_hex64(0xCBF29CE484222325) == "cbf29ce484222325"


class TestMinHashAccessors:
    def test_num_perm_accessor(self) -> None:
        a = MinHasher(42)
        assert a.num_perm == 42
        assert len(a.signature) == 42
