//! SimHash — locality-sensitive fingerprinting via FNV-1a.
//! Produces 64-bit or 128-bit fingerprints. Hamming distance for similarity.

use alloc::vec::Vec;

/// FNV-1a 64-bit constants.
const FNV64_OFFSET: u64 = 0xcbf29ce484222325;
const FNV64_PRIME: u64 = 0x100000001b3;

/// FNV-1a 64-bit hash.
pub fn fnv1a64(data: &[u8]) -> u64 {
    let mut h = FNV64_OFFSET;
    for &b in data {
        h ^= u64::from(b);
        h = h.wrapping_mul(FNV64_PRIME);
    }
    h
}

/// Compute 64-bit SimHash from a list of token strings.
///
/// Bit `i` (LSB first) is set iff the signed weight of bit `i` across all
/// token hashes is strictly positive.
pub fn simhash64(tokens: &[&str]) -> u64 {
    let mut v = [0i64; 64];
    for token in tokens {
        let h = fnv1a64(token.as_bytes());
        for (i, slot) in v.iter_mut().enumerate() {
            if (h >> i) & 1 == 1 {
                *slot += 1;
            } else {
                *slot -= 1;
            }
        }
    }
    let mut result: u64 = 0;
    for (i, &w) in v.iter().enumerate() {
        if w > 0 {
            result |= 1u64 << i;
        }
    }
    result
}

/// Compute 128-bit SimHash from a list of token strings.
///
/// Returns `(hi, lo)`: `lo` accumulates `fnv1a64(utf8(token))` bits and `hi`
/// accumulates `fnv1a64(utf8(token) || 0xFF)` bits.
pub fn simhash128(tokens: &[&str]) -> (u64, u64) {
    let mut v = [0i64; 128];
    for token in tokens {
        let bytes = token.as_bytes();
        let h1 = fnv1a64(bytes);
        let mut h2_input = Vec::with_capacity(bytes.len() + 1);
        h2_input.extend_from_slice(bytes);
        h2_input.push(0xff);
        let h2 = fnv1a64(&h2_input);
        for i in 0..64 {
            if (h1 >> i) & 1 == 1 {
                v[i] += 1;
            } else {
                v[i] -= 1;
            }
            if (h2 >> i) & 1 == 1 {
                v[64 + i] += 1;
            } else {
                v[64 + i] -= 1;
            }
        }
    }
    let mut lo: u64 = 0;
    let mut hi: u64 = 0;
    for i in 0..64 {
        if v[i] > 0 {
            lo |= 1u64 << i;
        }
        if v[64 + i] > 0 {
            hi |= 1u64 << i;
        }
    }
    (hi, lo)
}

/// Hamming distance between two 64-bit values.
pub fn hamming64(a: u64, b: u64) -> u32 {
    (a ^ b).count_ones()
}

/// Hamming distance between two 128-bit values (as high/low pairs).
pub fn hamming128(a: (u64, u64), b: (u64, u64)) -> u32 {
    (a.0 ^ b.0).count_ones() + (a.1 ^ b.1).count_ones()
}

/// Convenience: tokenize text with the SPEC whitespace set and compute simhash64.
pub fn simhash64_text(text: &str) -> u64 {
    simhash64(&crate::text::tokenize(text))
}

/// Convenience: tokenize text with the SPEC whitespace set and compute simhash128.
pub fn simhash128_text(text: &str) -> (u64, u64) {
    simhash128(&crate::text::tokenize(text))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fnv1a64() {
        assert_eq!(fnv1a64(b""), FNV64_OFFSET);
        assert_eq!(format!("{:016x}", fnv1a64(b"hello")), "a430d84680aabd0b");
    }

    #[test]
    fn test_simhash64_fox() {
        let h = simhash64_text("the quick brown fox jumps over the lazy dog");
        assert_eq!(format!("{:016x}", h), "cab7991c5475edee");
    }

    #[test]
    fn test_simhash64_cat() {
        let h = simhash64_text("the quick brown cat jumps over the lazy dog");
        assert_eq!(format!("{:016x}", h), "c2e7991c1465e56f");
    }

    #[test]
    fn test_hamming64_fox_cat() {
        let fox = simhash64_text("the quick brown fox jumps over the lazy dog");
        let cat = simhash64_text("the quick brown cat jumps over the lazy dog");
        assert_eq!(hamming64(fox, cat), 8);
    }

    #[test]
    fn test_identical() {
        let a = simhash64_text("hello world");
        let b = simhash64_text("hello world");
        assert_eq!(hamming64(a, b), 0);
    }

    #[test]
    fn test_empty_tokens() {
        assert_eq!(simhash64(&[]), 0);
        assert_eq!(simhash64_text("   \t\n"), 0);
    }
}
