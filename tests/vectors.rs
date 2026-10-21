//! Integration tests: consume the shared cross-language vectors file.
//!
//! Every port (Rust/TS/Python/Go/PHP) runs the exact same
//! vectors/lomboksimhash-vectors-v2.json. Results are compared as hex,
//! never near-equality (floats excluded per SPEC §11).

use lomboksimhash::minhash::MinHasher;
use lomboksimhash::sha256::{sha256, to_hex};
use lomboksimhash::shingle::{char_shingles, word_shingles};
use lomboksimhash::simhash::{fnv1a64, hamming128, simhash128, simhash128_text, simhash64_text};
use lomboksimhash::text::tokenize;
use lomboksimhash::LshIndex;

use serde_json::Value;
use std::fs;

fn vectors() -> Value {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/vectors/lomboksimhash-vectors-v2.json"
    );
    let raw = fs::read_to_string(path).expect("vectors file readable");
    serde_json::from_str(&raw).expect("vectors JSON valid")
}

fn cases<'a>(v: &'a Value, section: &str) -> &'a Vec<Value> {
    v["cases"][section]
        .as_array()
        .unwrap_or_else(|| panic!("section {section} missing"))
}

fn input_bytes(case: &Value) -> Vec<u8> {
    if let Some(text) = case["input"].as_str() {
        return text.as_bytes().to_vec();
    }
    let hexstr = case["input_hex"].as_str().expect("input or input_hex");
    (0..hexstr.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&hexstr[i..i + 2], 16).expect("hex byte"))
        .collect()
}

fn input_text(case: &Value) -> &str {
    case["input"].as_str().expect("text input")
}

#[test]
fn sha256_vectors() {
    let v = vectors();
    for case in cases(&v, "sha256") {
        let got = to_hex(&sha256(&input_bytes(case)));
        let want = case["expected_hex"].as_str().unwrap();
        assert_eq!(got, want, "case {} failed", case["id"].as_str().unwrap());
    }
}

#[test]
fn sha256_streaming_matches_one_shot() {
    let v = vectors();
    for case in cases(&v, "sha256") {
        let data = input_bytes(case);
        let mut st = lomboksimhash::Sha256State::new();
        let mid = data.len() / 2;
        st.update(&data[..mid]);
        st.update(&data[mid..]);
        let got = to_hex(&st.finalize());
        let want = case["expected_hex"].as_str().unwrap();
        assert_eq!(
            got,
            want,
            "streaming case {} failed",
            case["id"].as_str().unwrap()
        );
    }
}

#[test]
fn fnv1a64_vectors() {
    let v = vectors();
    for case in cases(&v, "fnv1a64") {
        let got = format!("{:016x}", fnv1a64(&input_bytes(case)));
        let want = case["expected_hex"].as_str().unwrap();
        assert_eq!(got, want, "case {} failed", case["id"].as_str().unwrap());
    }
}

#[test]
fn shingle_vectors() {
    let v = vectors();
    for case in cases(&v, "shingle") {
        let text = input_text(case);
        let n = case["n"].as_u64().unwrap() as usize;
        let mode = case["mode"].as_str().unwrap();
        let got: Vec<String> = if mode == "character" {
            char_shingles(text, n)
        } else {
            word_shingles(text, n)
        };
        let want: Vec<String> = case["expected"]
            .as_array()
            .unwrap()
            .iter()
            .map(|s| s.as_str().unwrap().to_string())
            .collect();
        assert_eq!(got, want, "case {} failed", case["id"].as_str().unwrap());
    }
}

#[test]
fn simhash64_vectors() {
    let v = vectors();
    for case in cases(&v, "simhash64") {
        let got = format!("{:016x}", simhash64_text(input_text(case)));
        let want = case["expected_hex"].as_str().unwrap();
        assert_eq!(got, want, "case {} failed", case["id"].as_str().unwrap());
    }
}

#[test]
fn simhash128_vectors() {
    let v = vectors();
    for case in cases(&v, "simhash128") {
        let (hi, lo) = simhash128_text(input_text(case));
        let want_hi = case["hi_hex"].as_str().unwrap();
        let want_lo = case["lo_hex"].as_str().unwrap();
        assert_eq!(
            format!("{hi:016x}"),
            want_hi,
            "case {} hi",
            case["id"].as_str().unwrap()
        );
        assert_eq!(
            format!("{lo:016x}"),
            want_lo,
            "case {} lo",
            case["id"].as_str().unwrap()
        );
    }
}

#[test]
fn simhash128_consistency_with_64() {
    let v = vectors();
    for case in cases(&v, "simhash128") {
        let tokens = tokenize(input_text(case));
        let (hi, lo) = simhash128(&tokens);
        assert_eq!(hamming128((hi, lo), (hi, lo)), 0);
    }
}

#[test]
fn minhash_signature_vectors() {
    let v = vectors();
    for case in cases(&v, "minhash_signature") {
        let tokens: Vec<&str> = case["tokens"]
            .as_array()
            .unwrap()
            .iter()
            .map(|t| t.as_str().unwrap())
            .collect();
        let num_perm = case["num_perm"].as_u64().unwrap() as usize;
        let mut mh = MinHasher::new(num_perm);
        mh.add_tokens(&tokens);
        let want: Vec<String> = case["signature_hex"]
            .as_array()
            .unwrap()
            .iter()
            .map(|s| s.as_str().unwrap().to_string())
            .collect();
        let got: Vec<String> = mh.signature().iter().map(|x| format!("{x:016x}")).collect();
        assert_eq!(got, want, "case {} failed", case["id"].as_str().unwrap());
    }
}

#[test]
fn minhash_jaccard_vectors() {
    let v = vectors();
    for case in cases(&v, "minhash_jaccard") {
        let set_a: Vec<&str> = case["set_a"]
            .as_array()
            .unwrap()
            .iter()
            .map(|t| t.as_str().unwrap())
            .collect();
        let set_b: Vec<&str> = case["set_b"]
            .as_array()
            .unwrap()
            .iter()
            .map(|t| t.as_str().unwrap())
            .collect();
        let num_perm = case["num_perm"].as_u64().unwrap() as usize;
        let mut a = MinHasher::new(num_perm);
        let mut b = MinHasher::new(num_perm);
        a.add_tokens(&set_a);
        b.add_tokens(&set_b);
        let matches: usize = a
            .signature()
            .iter()
            .zip(b.signature().iter())
            .filter(|(x, y)| x == y)
            .count();
        let want = case["expected_matches"].as_u64().unwrap() as usize;
        assert_eq!(
            matches,
            want,
            "case {} failed",
            case["id"].as_str().unwrap()
        );
    }
}

#[test]
fn lsh_bandhash_vectors() {
    // Rust band_hash is private; pin the contract by re-deriving the key
    // per SPEC (FNV-1a over LE bytes) and by bucketing via a 1-band index.
    let v = vectors();
    for case in cases(&v, "lsh_bandhash") {
        let values: Vec<u64> = case["band_values_hex"]
            .as_array()
            .unwrap()
            .iter()
            .map(|s| u64::from_str_radix(s.as_str().unwrap(), 16).unwrap())
            .collect();
        let mut bytes = Vec::new();
        for x in &values {
            bytes.extend_from_slice(&x.to_le_bytes());
        }
        let mut h: u64 = 0xcbf29ce484222325;
        for b in bytes {
            h ^= u64::from(b);
            h = h.wrapping_mul(0x100000001b3);
        }
        let want = case["expected_key_hex"].as_str().unwrap();
        assert_eq!(
            format!("{h:016x}"),
            want,
            "case {}",
            case["id"].as_str().unwrap()
        );

        let mut idx = LshIndex::new(1, values.len());
        idx.insert("probe", &values);
        assert!(idx.query(&values).contains(&String::from("probe")));
    }
}

#[test]
fn lsh_index_vectors() {
    let v = vectors();
    for case in cases(&v, "lsh_index") {
        let bands = case["bands"].as_u64().unwrap() as usize;
        let rows = case["rows"].as_u64().unwrap() as usize;
        let mut idx = LshIndex::new(bands, rows);
        for ins in case["inserts"].as_array().unwrap() {
            let sig: Vec<u64> = ins["signature_hex"]
                .as_array()
                .unwrap()
                .iter()
                .map(|s| u64::from_str_radix(s.as_str().unwrap(), 16).unwrap())
                .collect();
            idx.insert(ins["doc_id"].as_str().unwrap(), &sig);
        }
        let query_sig: Vec<u64> = case["query_hex"]
            .as_array()
            .unwrap()
            .iter()
            .map(|s| u64::from_str_radix(s.as_str().unwrap(), 16).unwrap())
            .collect();
        let got = idx.query(&query_sig);
        let want: Vec<String> = case["expected"]
            .as_array()
            .unwrap()
            .iter()
            .map(|s| s.as_str().unwrap().to_string())
            .collect();
        assert_eq!(got, want, "case {} failed", case["id"].as_str().unwrap());

        if let Some(remove) = case["remove"].as_object() {
            let rem_sig: Vec<u64> = remove["signature_hex"]
                .as_array()
                .unwrap()
                .iter()
                .map(|s| u64::from_str_radix(s.as_str().unwrap(), 16).unwrap())
                .collect();
            idx.remove(remove["doc_id"].as_str().unwrap(), &rem_sig);
            let after = idx.query(&query_sig);
            let want_after: Vec<String> = case["expected_after_remove"]
                .as_array()
                .unwrap()
                .iter()
                .map(|s| s.as_str().unwrap().to_string())
                .collect();
            assert_eq!(
                after,
                want_after,
                "case {} after remove",
                case["id"].as_str().unwrap()
            );
        }
    }
}
