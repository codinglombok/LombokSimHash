//! # LombokSimHash
//!
//! Near-duplicate document detection for RAG pipelines.
//! Zero-dependency, no_std compatible.
//!
//! ## Features
//! - **SimHash** — 64/128-bit text fingerprinting via FNV-1a
//! - **MinHash** — Jaccard similarity estimation via k-permutation
//! - **LSH** — Band+row locality-sensitive hashing for approximate nearest neighbors
//! - **SHA-256** — Pure implementation (FIPS 180-4) for exact content dedup
//! - **Shingling** — Character/word n-gram generation with streaming API
//!
//! Part of [LombokRAGFrameworks](https://github.com/codinglombok/LombokRAGFrameworks).

#![cfg_attr(not(feature = "std"), no_std)]

extern crate alloc;

pub mod sha256;
pub mod shingle;
pub mod simhash;
pub mod minhash;
pub mod lsh;

pub use sha256::{sha256, Sha256State};
pub use shingle::{Shingler, ShingleMode};
pub use simhash::{simhash64, simhash128, simhash64_text, simhash128_text, hamming64, hamming128};
pub use minhash::{MinHasher, jaccard_estimate};
pub use lsh::LshIndex;
