//! Shingling — n-gram generation for document fingerprinting.
//! Supports character and word modes with streaming API.

use alloc::string::String;
use alloc::vec::Vec;
use alloc::collections::BTreeSet;

/// Shingle generation mode.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum ShingleMode {
    /// Character n-grams
    Character,
    /// Word n-grams
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
    pub fn new(mode: ShingleMode, n: usize) -> Self {
        assert!(n > 0, "shingle size must be > 0");
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

    /// Finish and return all unique shingles.
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
        let words: Vec<&str> = self.buffer.split_whitespace().collect();
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

/// Convenience: generate character shingles from text.
pub fn char_shingles(text: &str, n: usize) -> Vec<String> {
    let mut s = Shingler::new(ShingleMode::Character, n);
    s.feed(text);
    s.finish_vec()
}

/// Convenience: generate word shingles from text.
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
        let shingles = char_shingles("abcde", 3);
        assert_eq!(shingles, vec!["abc", "bcd", "cde"]);
    }

    #[test]
    fn test_word_shingles() {
        let shingles = word_shingles("the quick brown fox", 2);
        assert!(shingles.contains(&String::from("the quick")));
        assert!(shingles.contains(&String::from("quick brown")));
        assert!(shingles.contains(&String::from("brown fox")));
    }

    #[test]
    fn test_streaming() {
        let mut s = Shingler::new(ShingleMode::Character, 3);
        s.feed("abc");
        s.feed("de");
        let shingles = s.finish_vec();
        assert_eq!(shingles, vec!["abc", "bcd", "cde"]);
    }
}
