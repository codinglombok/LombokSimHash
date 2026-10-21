"""SHA-256 (FIPS 180-4) — pure implementation.

Behavior pinned by docs/SPEC_LombokSimHash_0.1.0.md; vectors in
vectors/lomboksimhash-vectors-v2.json.
"""

from __future__ import annotations

import struct

_MASK32 = 0xFFFFFFFF

_K_SHA = [
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5,
    0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
    0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
    0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
    0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC,
    0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
    0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7,
    0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
    0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
    0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
    0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3,
    0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
    0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5,
    0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
    0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
    0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
]

_H_INIT = [
    0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
    0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19,
]


def _rotr32(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & _MASK32


def _sha256_compress(state: list[int], block: bytes) -> None:
    w = [0] * 64
    for i in range(16):
        w[i] = struct.unpack(">I", block[i * 4:i * 4 + 4])[0]
    for i in range(16, 64):
        s0 = _rotr32(w[i - 15], 7) ^ _rotr32(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr32(w[i - 2], 17) ^ _rotr32(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & _MASK32

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

    for i, v in enumerate((a, b, c, d, e, f, g, h)):
        state[i] = (state[i] + v) & _MASK32


class Sha256State:
    """Incremental SHA-256 hasher (streaming)."""

    __slots__ = ("_state", "_buffer", "_total_len")

    def __init__(self) -> None:
        self._state = list(_H_INIT)
        self._buffer = bytearray()
        self._total_len = 0

    def update(self, data: bytes | bytearray | memoryview) -> None:
        self._total_len += len(data)
        self._buffer.extend(data)
        while len(self._buffer) >= 64:
            block = bytes(self._buffer[:64])
            del self._buffer[:64]
            _sha256_compress(self._state, block)

    def digest(self) -> bytes:
        """Finalize (without destroying state) and return the 32-byte digest."""
        state = list(self._state)
        buffer = bytearray(self._buffer)
        bit_len = self._total_len * 8
        buffer.append(0x80)
        while len(buffer) % 64 != 56:
            buffer.append(0x00)
        buffer.extend(bit_len.to_bytes(8, "big"))
        for i in range(0, len(buffer), 64):
            _sha256_compress(state, bytes(buffer[i:i + 64]))
        return b"".join(v.to_bytes(4, "big") for v in state)

    def hexdigest(self) -> str:
        return self.digest().hex()

    def finalize(self) -> bytes:
        """Finalize and return the 32-byte digest."""
        return self.digest()


def sha256(data: bytes | str) -> str:
    """Compute SHA-256 of bytes or UTF-8 text. Returns lowercase hex string."""
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
        _sha256_compress(state, bytes(padded[i:i + 64]))

    return "".join(f"{v:08x}" for v in state)


def to_hex(digest: bytes) -> str:
    """Convert digest bytes to lowercase hex string."""
    return digest.hex()
