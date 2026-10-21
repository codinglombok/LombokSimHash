//! LombokSimHash
//!
//! Near-duplicate document detection for RAG pipelines.
//! Zero dependencies, `no_std` compatible (core + alloc only).
//!
//! ## Features
//! - **SimHash** — 64/128-bit text fingerprinting via FNV-1a
//! - **MinHash** — Jaccard similarity estimation via k-permutation
//! - **LSH** — Band+row locality-sensitive hashing for approximate nearest neighbors
//! - **SHA-256** — Pure implementation (FIPS 180-4) for exact content dedup
//! - **Shingling** — Character/word n-gram generation with streaming API
//!
//! Behavior is pinned by `docs/SPEC_LombokSimHash_0.1.0.md`; all ports are
//! validated against `vectors/lomboksimhash-vectors-v2.json` (bit-identical).
//!
//! Part of [LombokRAGFrameworks](https://github.com/codinglombok/LombokRAGFrameworks).

#![cfg_attr(not(feature = "std"), no_std)]
#![warn(missing_docs)]

extern crate alloc;

pub mod lsh;
pub mod minhash;
pub mod sha256;
pub mod shingle;
pub mod simhash;
pub mod text;

pub use lsh::LshIndex;
pub use minhash::{jaccard_estimate, MinHasher};
pub use sha256::{sha256, to_hex, Sha256State};
pub use shingle::{char_shingles, word_shingles, ShingleMode, Shingler};
pub use simhash::{
    fnv1a64, hamming128, hamming64, simhash128, simhash128_text, simhash64, simhash64_text,
};
pub use text::tokenize;
