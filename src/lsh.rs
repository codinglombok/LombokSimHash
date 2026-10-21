//! LSH — Locality-Sensitive Hashing for approximate nearest neighbors.
//! Band+row technique over MinHash signatures.

use alloc::collections::{BTreeMap, BTreeSet};
use alloc::string::String;
use alloc::vec::Vec;

/// LSH Index using band+row technique.
pub struct LshIndex {
    bands: usize,
    rows: usize,
    /// buckets[band_idx] -> hash -> list of doc IDs (insertion order)
    buckets: Vec<BTreeMap<u64, Vec<String>>>,
}

impl LshIndex {
    /// Create a new LSH index.
    ///
    /// `bands * rows` must equal the MinHash signature length.
    ///
    /// # Panics
    /// Panics with `[ERR_LSH_CONFIG]` when `bands == 0` or `rows == 0`.
    pub fn new(bands: usize, rows: usize) -> Self {
        if bands == 0 || rows == 0 {
            panic!("[ERR_LSH_CONFIG] bands and rows must be > 0");
        }
        let buckets = (0..bands).map(|_| BTreeMap::new()).collect();
        Self {
            bands,
            rows,
            buckets,
        }
    }

    /// Number of bands.
    pub fn bands(&self) -> usize {
        self.bands
    }

    /// Number of rows per band.
    pub fn rows(&self) -> usize {
        self.rows
    }

    /// Required MinHash signature length.
    pub fn signature_len(&self) -> usize {
        self.bands * self.rows
    }

    /// Compute the approximate Jaccard threshold `(1/bands)^(1/rows)`.
    ///
    /// Implemented with a Newton-Raphson n-th root so the crate stays
    /// `no_std`-compatible (no `powf`). Accuracy is better than 1e-12;
    /// this value is informational and NOT part of the bit-identical
    /// contract (floating point).
    pub fn threshold(&self) -> f64 {
        let y = 1.0 / self.bands as f64;
        let r = self.rows as f64;
        // Newton iteration for f(t) = t^rows - y.
        let mut x = y;
        for _ in 0..64 {
            let prev_pow = powi_f64(x, self.rows - 1);
            let next = ((r - 1.0) * x + y / prev_pow) / r;
            let delta = (next - x).abs();
            x = next;
            if delta < 1e-16 {
                break;
            }
        }
        x
    }

    /// Hash a band (sub-slice of signature) to a bucket key:
    /// FNV-1a 64 over the little-endian bytes of each value.
    fn band_hash(band_values: &[u64]) -> u64 {
        crate::simhash::fnv1a64(
            &band_values
                .iter()
                .flat_map(|v| v.to_le_bytes())
                .collect::<Vec<u8>>(),
        )
    }

    /// Insert a document's MinHash signature into the index.
    ///
    /// # Panics
    /// Panics with `[ERR_SIG_LEN]` when `signature.len() != bands * rows`.
    pub fn insert(&mut self, doc_id: &str, signature: &[u64]) {
        self.assert_signature_len(signature);
        for band_idx in 0..self.bands {
            let start = band_idx * self.rows;
            let band_values = &signature[start..start + self.rows];
            let bucket_key = Self::band_hash(band_values);
            self.buckets[band_idx]
                .entry(bucket_key)
                .or_default()
                .push(String::from(doc_id));
        }
    }

    /// Query for candidate near-duplicates.
    ///
    /// Returns de-duplicated doc IDs sorted ascending by code point.
    ///
    /// # Panics
    /// Panics with `[ERR_SIG_LEN]` when `signature.len() != bands * rows`.
    pub fn query(&self, signature: &[u64]) -> Vec<String> {
        self.assert_signature_len(signature);
        let mut candidates = BTreeSet::new();
        for band_idx in 0..self.bands {
            let start = band_idx * self.rows;
            let band_values = &signature[start..start + self.rows];
            let bucket_key = Self::band_hash(band_values);
            if let Some(docs) = self.buckets[band_idx].get(&bucket_key) {
                for doc in docs {
                    candidates.insert(doc.clone());
                }
            }
        }
        candidates.into_iter().collect()
    }

    /// Remove a document from every band bucket touched by the signature.
    ///
    /// # Panics
    /// Panics with `[ERR_SIG_LEN]` when `signature.len() != bands * rows`.
    pub fn remove(&mut self, doc_id: &str, signature: &[u64]) {
        self.assert_signature_len(signature);
        for band_idx in 0..self.bands {
            let start = band_idx * self.rows;
            let band_values = &signature[start..start + self.rows];
            let bucket_key = Self::band_hash(band_values);
            if let Some(docs) = self.buckets[band_idx].get_mut(&bucket_key) {
                docs.retain(|d| d != doc_id);
            }
        }
    }

    fn assert_signature_len(&self, signature: &[u64]) {
        if signature.len() != self.signature_len() {
            panic!(
                "[ERR_SIG_LEN] signature length must be bands * rows = {}",
                self.signature_len()
            );
        }
    }
}

/// Integer-exponent power using only core arithmetic.
fn powi_f64(mut base: f64, mut e: usize) -> f64 {
    let mut acc = 1.0;
    while e > 0 {
        if e & 1 == 1 {
            acc *= base;
        }
        base *= base;
        e >>= 1;
    }
    acc
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::minhash::MinHasher;

    #[test]
    fn test_threshold() {
        let idx = LshIndex::new(20, 5);
        let t = idx.threshold();
        // (1/20)^(1/5) ≈ 0.5493
        assert!((t - 0.5493).abs() < 0.01, "threshold = {t}");
    }

    #[test]
    fn test_threshold_edge_configs() {
        assert_eq!(LshIndex::new(1, 1).threshold(), 1.0);
        let t = LshIndex::new(4, 2).threshold();
        assert!((t - 0.5).abs() < 1e-9, "threshold = {t}");
    }

    #[test]
    fn test_insert_query_identical() {
        let num_perm = 100; // 20 bands * 5 rows
        let mut idx = LshIndex::new(20, 5);

        let mut mh = MinHasher::new(num_perm);
        mh.add_tokens(&["the", "quick", "brown", "fox"]);
        idx.insert("doc1", mh.signature());

        let candidates = idx.query(mh.signature());
        assert!(candidates.contains(&String::from("doc1")));
    }

    #[test]
    fn test_query_sorted() {
        let mut idx = LshIndex::new(3, 1);
        let sig = [1u64, 2, 3];
        idx.insert("b_doc", &sig);
        idx.insert("a_doc", &sig);
        idx.insert("c_doc", &sig);
        assert_eq!(
            idx.query(&sig),
            vec![
                String::from("a_doc"),
                String::from("b_doc"),
                String::from("c_doc")
            ]
        );
    }

    #[test]
    fn test_remove() {
        let num_perm = 100;
        let mut idx = LshIndex::new(20, 5);

        let mut mh = MinHasher::new(num_perm);
        mh.add_tokens(&["hello", "world"]);
        let sig = mh.signature().to_vec();

        idx.insert("doc1", &sig);
        idx.remove("doc1", &sig);

        let candidates = idx.query(&sig);
        assert!(!candidates.contains(&String::from("doc1")));
    }

    #[test]
    #[should_panic(expected = "[ERR_SIG_LEN] signature length must be bands * rows = 10")]
    fn test_insert_wrong_len_panics() {
        let mut idx = LshIndex::new(5, 2);
        idx.insert("doc", &[1, 2, 3]);
    }

    #[test]
    #[should_panic(expected = "[ERR_LSH_CONFIG] bands and rows must be > 0")]
    fn test_zero_bands_panics() {
        let _ = LshIndex::new(0, 5);
    }
}
