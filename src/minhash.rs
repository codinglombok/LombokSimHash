//! MinHash — Jaccard similarity estimation via k-permutation.
//! Uses deterministic LCG seeding and Mersenne prime universal hash.

use alloc::vec::Vec;

use crate::simhash::fnv1a64;

/// Mersenne prime for universal hash: 2^61 - 1
const MERSENNE_61: u64 = (1u64 << 61) - 1;

/// LCG parameters for deterministic seed generation.
const LCG_SEED: u64 = 0x517cc1b727220a95;
const LCG_MUL: u64 = 6364136223846793005;
const LCG_INC: u64 = 1442695040888963407;

/// Generate `(a, b)` pairs for the universal hash family using the SPEC LCG.
///
/// Per permutation: two LCG steps; `a = state % p` (with `a = 1` when the
/// modulus is zero), then `b = state % p`. `p = 2^61 - 1`.
fn generate_hash_params(num_perm: usize) -> Vec<(u64, u64)> {
    let mut state = LCG_SEED;
    let mut params = Vec::with_capacity(num_perm);
    for _ in 0..num_perm {
        state = state.wrapping_mul(LCG_MUL).wrapping_add(LCG_INC);
        let a = (state % MERSENNE_61).max(1);
        state = state.wrapping_mul(LCG_MUL).wrapping_add(LCG_INC);
        let b = state % MERSENNE_61;
        params.push((a, b));
    }
    params
}

/// Universal hash: `(a * (x mod p) + b) mod p` with `p = 2^61 - 1`.
fn universal_hash(a: u64, b: u64, x: u64) -> u64 {
    let x_mod = x % MERSENNE_61;
    // 128-bit intermediate avoids overflow: a < p, x_mod < p, b < p.
    let ax = (u128::from(a)) * (u128::from(x_mod));
    let axb = ax + u128::from(b);
    u64::try_from(axb % (u128::from(MERSENNE_61))).expect("result < p < 2^61")
}

/// MinHash signature generator.
pub struct MinHasher {
    num_perm: usize,
    params: Vec<(u64, u64)>,
    signature: Vec<u64>,
}

impl MinHasher {
    /// Create a new MinHasher with `num_perm` permutations.
    ///
    /// # Panics
    /// Panics with `[ERR_MINHASH_PERM]` when `num_perm == 0`.
    pub fn new(num_perm: usize) -> Self {
        if num_perm == 0 {
            panic!("[ERR_MINHASH_PERM] num_perm must be > 0");
        }
        let params = generate_hash_params(num_perm);
        let mut signature = Vec::new();
        signature.resize(num_perm, u64::MAX);
        Self {
            num_perm,
            params,
            signature,
        }
    }

    /// Add a token to the MinHash signature (idempotent per distinct token).
    pub fn add(&mut self, token: &str) {
        let h = fnv1a64(token.as_bytes());
        for i in 0..self.num_perm {
            let (a, b) = self.params[i];
            let val = universal_hash(a, b, h);
            if val < self.signature[i] {
                self.signature[i] = val;
            }
        }
    }

    /// Add multiple tokens (order-independent).
    pub fn add_tokens(&mut self, tokens: &[&str]) {
        for token in tokens {
            self.add(token);
        }
    }

    /// Get the MinHash signature.
    pub fn signature(&self) -> &[u64] {
        &self.signature
    }

    /// Number of permutations.
    pub fn num_perm(&self) -> usize {
        self.num_perm
    }
}

/// Estimate Jaccard similarity between two MinHash signatures.
///
/// # Panics
/// Panics with `[ERR_JACCARD_LEN]` on length mismatch and
/// `[ERR_JACCARD_EMPTY]` when signatures are empty.
pub fn jaccard_estimate(sig_a: &[u64], sig_b: &[u64]) -> f64 {
    if sig_a.len() != sig_b.len() {
        panic!("[ERR_JACCARD_LEN] signatures must have same length");
    }
    if sig_a.is_empty() {
        panic!("[ERR_JACCARD_EMPTY] signatures must not be empty");
    }
    let matches = sig_a
        .iter()
        .zip(sig_b.iter())
        .filter(|(a, b)| a == b)
        .count();
    f64::from(u32::try_from(matches).expect("len fits u32")) / sig_a.len() as f64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_identical_sets() {
        let mut a = MinHasher::new(128);
        let mut b = MinHasher::new(128);
        let tokens = vec!["the", "quick", "brown", "fox"];
        a.add_tokens(&tokens);
        b.add_tokens(&tokens);
        assert_eq!(jaccard_estimate(a.signature(), b.signature()), 1.0);
    }

    #[test]
    fn test_disjoint_sets() {
        let mut a = MinHasher::new(128);
        let mut b = MinHasher::new(128);
        a.add_tokens(&["alpha", "beta", "gamma"]);
        b.add_tokens(&["delta", "epsilon", "zeta"]);
        let j = jaccard_estimate(a.signature(), b.signature());
        assert!(j < 0.2, "disjoint sets should have low Jaccard: {j}");
    }

    #[test]
    fn test_overlapping_sets() {
        let mut a = MinHasher::new(128);
        let mut b = MinHasher::new(128);
        a.add_tokens(&["a", "b", "c", "d"]);
        b.add_tokens(&["c", "d", "e", "f"]);
        let j = jaccard_estimate(a.signature(), b.signature());
        // Actual Jaccard = 2/6 = 0.333
        assert!(j > 0.1 && j < 0.6, "should approximate 0.33: {j}");
    }

    #[test]
    fn test_deterministic() {
        let mut a = MinHasher::new(64);
        let mut b = MinHasher::new(64);
        a.add_tokens(&["hello", "world"]);
        b.add_tokens(&["hello", "world"]);
        assert_eq!(a.signature(), b.signature());
    }

    #[test]
    fn test_duplicate_tokens_idempotent() {
        let mut a = MinHasher::new(32);
        let mut b = MinHasher::new(32);
        a.add_tokens(&["a", "a", "b"]);
        b.add_tokens(&["a", "b"]);
        assert_eq!(a.signature(), b.signature());
    }

    #[test]
    #[should_panic(expected = "[ERR_MINHASH_PERM] num_perm must be > 0")]
    fn test_zero_perm_panics() {
        let _ = MinHasher::new(0);
    }

    #[test]
    #[should_panic(expected = "[ERR_JACCARD_LEN] signatures must have same length")]
    fn test_jaccard_len_mismatch_panics() {
        let _ = jaccard_estimate(&[1, 2], &[1]);
    }

    #[test]
    #[should_panic(expected = "[ERR_JACCARD_EMPTY] signatures must not be empty")]
    fn test_jaccard_empty_panics() {
        let _ = jaccard_estimate(&[], &[]);
    }
}
