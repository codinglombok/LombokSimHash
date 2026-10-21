//! Shingling — n-gram generation for document fingerprinting.
//! Supports character and word modes with streaming API.

use alloc::collections::BTreeSet;
use alloc::string::String;
use alloc::vec::Vec;

/// Shingle generation mode.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ShingleMode {
    /// Character n-grams (Unicode code points)
    Character,
    /// Word n-grams (SPEC tokenizer, joined with a single space)
    Word,
}

/// Streaming shingle generator.
pub struct Shingler {
    mode: ShingleMode,
    n: usize,
    buffer: String,
}

impl Shingler {
    /// Create a new shingler with the given mode and n-gram size.
    ///
    /// # Panics
    /// Panics with `[ERR_SHINGLE_N]` when `n == 0`.
    pub fn new(mode: ShingleMode, n: usize) -> Self {
        if n == 0 {
            panic!("[ERR_SHINGLE_N] shingle size must be > 0");
        }
        Self {
            mode,
            n,
            buffer: String::new(),
        }
    }

    /// Feed text into the shingler (streaming).
    pub fn feed(&mut self, text: &str) {
        self.buffer.push_str(text);
    }

    /// Finish and return all unique shingles (sorted by code point).
    pub fn finish(&self) -> BTreeSet<String> {
        match self.mode {
            ShingleMode::Character => self.char_shingles(),
            ShingleMode::Word => self.word_shingles(),
        }
    }

    /// Return shingles as a sorted Vec.
    pub fn finish_vec(&self) -> Vec<String> {
        self.finish().into_iter().collect()
    }

    /// N-gram size.
    pub fn n(&self) -> usize {
        self.n
    }

    /// Mode.
    pub fn mode(&self) -> ShingleMode {
        self.mode
    }

    fn char_shingles(&self) -> BTreeSet<String> {
        let chars: Vec<char> = self.buffer.chars().collect();
        let mut set = BTreeSet::new();
        if chars.len() >= self.n {
            for i in 0..=chars.len() - self.n {
                let s: String = chars[i..i + self.n].iter().collect();
                set.insert(s);
            }
        }
        set
    }

    fn word_shingles(&self) -> BTreeSet<String> {
        let words = crate::text::tokenize(&self.buffer);
        let mut set = BTreeSet::new();
        if words.len() >= self.n {
            for i in 0..=words.len() - self.n {
                let s = words[i..i + self.n].join(" ");
                set.insert(s);
            }
        }
        set
    }
}

/// Convenience: generate character shingles from text (code points).
///
/// # Panics
/// Panics with `[ERR_SHINGLE_N]` when `n == 0`.
pub fn char_shingles(text: &str, n: usize) -> Vec<String> {
    let mut s = Shingler::new(ShingleMode::Character, n);
    s.feed(text);
    s.finish_vec()
}

/// Convenience: generate word shingles from text (SPEC tokenizer).
///
/// # Panics
/// Panics with `[ERR_SHINGLE_N]` when `n == 0`.
pub fn word_shingles(text: &str, n: usize) -> Vec<String> {
    let mut s = Shingler::new(ShingleMode::Word, n);
    s.feed(text);
    s.finish_vec()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_char_shingles() {
        assert_eq!(char_shingles("abcde", 3), vec!["abc", "bcd", "cde"]);
    }

    #[test]
    fn test_word_shingles() {
        let shingles = word_shingles("the quick brown fox", 2);
        assert_eq!(shingles, vec!["brown fox", "quick brown", "the quick"]);
    }

    #[test]
    fn test_streaming() {
        let mut s = Shingler::new(ShingleMode::Character, 3);
        s.feed("abc");
        s.feed("de");
        assert_eq!(s.finish_vec(), vec!["abc", "bcd", "cde"]);
    }

    #[test]
    fn test_n_larger_than_input() {
        assert!(char_shingles("ab", 5).is_empty());
        assert!(word_shingles("a b", 4).is_empty());
    }

    #[test]
    #[should_panic(expected = "[ERR_SHINGLE_N] shingle size must be > 0")]
    fn test_zero_n_panics() {
        let _ = Shingler::new(ShingleMode::Character, 0);
    }
}
