//! LSH — Locality-Sensitive Hashing for approximate nearest neighbors.
//! Band+row technique over MinHash signatures.

use alloc::collections::BTreeMap;
use alloc::string::String;
use alloc::vec::Vec;

/// LSH Index using band+row technique.
pub struct LshIndex {
    bands: usize,
    rows: usize,
    /// buckets[band_idx] -> hash -> list of doc IDs
    buckets: Vec<BTreeMap<u64, Vec<String>>>,
}

impl LshIndex {
    /// Create a new LSH index.
    /// `bands * rows` must equal the MinHash signature length.
    pub fn new(bands: usize, rows: usize) -> Self {
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

    /// Compute the approximate Jaccard threshold for this configuration.
    /// Pairs with Jaccard >= threshold have high probability of being candidates.
    pub fn threshold(&self) -> f64 {
        (1.0 / self.bands as f64).powf(1.0 / self.rows as f64)
    }

    /// Hash a band (sub-slice of signature) to a bucket key.
    fn band_hash(band_values: &[u64]) -> u64 {
        let mut h: u64 = 0xcbf29ce484222325;
        for &val in band_values {
            for &byte in &val.to_le_bytes() {
                h ^= byte as u64;
                h = h.wrapping_mul(0x100000001b3);
            }
        }
        h
    }

    /// Insert a document's MinHash signature into the index.
    pub fn insert(&mut self, doc_id: &str, signature: &[u64]) {
        assert_eq!(
            signature.len(),
            self.signature_len(),
            "signature length must be bands * rows = {}",
            self.signature_len()
        );
        for band_idx in 0..self.bands {
            let start = band_idx * self.rows;
            let end = start + self.rows;
            let band_values = &signature[start..end];
            let bucket_key = Self::band_hash(band_values);
            self.buckets[band_idx]
                .entry(bucket_key)
                .or_insert_with(Vec::new)
                .push(String::from(doc_id));
        }
    }

    /// Query for candidate near-duplicates.
    pub fn query(&self, signature: &[u64]) -> Vec<String> {
        assert_eq!(
            signature.len(),
            self.signature_len(),
            "signature length must be bands * rows = {}",
            self.signature_len()
        );
        let mut candidates = alloc::collections::BTreeSet::new();
        for band_idx in 0..self.bands {
            let start = band_idx * self.rows;
            let end = start + self.rows;
            let band_values = &signature[start..end];
            let bucket_key = Self::band_hash(band_values);
            if let Some(docs) = self.buckets[band_idx].get(&bucket_key) {
                for doc in docs {
                    candidates.insert(doc.clone());
                }
            }
        }
        candidates.into_iter().collect()
    }

    /// Remove a document from the index.
    pub fn remove(&mut self, doc_id: &str, signature: &[u64]) {
        assert_eq!(signature.len(), self.signature_len());
        for band_idx in 0..self.bands {
            let start = band_idx * self.rows;
            let end = start + self.rows;
            let band_values = &signature[start..end];
            let bucket_key = Self::band_hash(band_values);
            if let Some(docs) = self.buckets[band_idx].get_mut(&bucket_key) {
                docs.retain(|d| d != doc_id);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::minhash::{MinHasher, jaccard_estimate};

    #[test]
    fn test_threshold() {
        let idx = LshIndex::new(20, 5);
        let t = idx.threshold();
        // (1/20)^(1/5) ≈ 0.5493
        assert!((t - 0.5493).abs() < 0.01, "threshold = {}", t);
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
}
