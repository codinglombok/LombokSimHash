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

/// Generate (a, b) pairs for universal hash family using LCG.
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

/// Universal hash: (a * x + b) mod (2^61 - 1)
fn universal_hash(a: u64, b: u64, x: u64) -> u64 {
    let x_mod = x % MERSENNE_61;
    // Use 128-bit arithmetic to avoid overflow
    let ax = (a as u128) * (x_mod as u128);
    let axb = ax + (b as u128);
    (axb % (MERSENNE_61 as u128)) as u64
}

/// MinHash signature generator.
pub struct MinHasher {
    num_perm: usize,
    params: Vec<(u64, u64)>,
    signature: Vec<u64>,
}

impl MinHasher {
    /// Create a new MinHasher with k permutations.
    pub fn new(num_perm: usize) -> Self {
        let params = generate_hash_params(num_perm);
        let signature = vec![u64::MAX; num_perm];
        Self {
            num_perm,
            params,
            signature,
        }
    }

    /// Add a token to the MinHash signature.
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

    /// Add multiple tokens.
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
pub fn jaccard_estimate(sig_a: &[u64], sig_b: &[u64]) -> f64 {
    assert_eq!(sig_a.len(), sig_b.len(), "signatures must have same length");
    let matches = sig_a.iter().zip(sig_b.iter()).filter(|(a, b)| a == b).count();
    matches as f64 / sig_a.len() as f64
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
        assert!(j < 0.2, "disjoint sets should have low Jaccard: {}", j);
    }

    #[test]
    fn test_overlapping_sets() {
        let mut a = MinHasher::new(128);
        let mut b = MinHasher::new(128);
        a.add_tokens(&["a", "b", "c", "d"]);
        b.add_tokens(&["c", "d", "e", "f"]);
        let j = jaccard_estimate(a.signature(), b.signature());
        // Actual Jaccard = 2/6 = 0.333
        assert!(j > 0.1 && j < 0.6, "should approximate 0.33: {}", j);
    }

    #[test]
    fn test_deterministic() {
        let mut a = MinHasher::new(64);
        let mut b = MinHasher::new(64);
        a.add_tokens(&["hello", "world"]);
        b.add_tokens(&["hello", "world"]);
        assert_eq!(a.signature(), b.signature());
    }
}
