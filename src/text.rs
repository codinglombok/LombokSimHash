//! Tokenization — exact cross-language whitespace contract.
//!
//! The SPEC whitespace set is the Unicode `White_Space` property
//! (25 code points). It is pinned explicitly so that every port splits
//! identically for every input (language built-ins differ: e.g. Python
//! also splits on U+001C..U+001F, JavaScript `\s` also matches U+FEFF).

/// Returns `true` for exactly the SPEC whitespace code points
/// (Unicode `White_Space` property).
pub fn is_spec_whitespace(c: char) -> bool {
    matches!(
        c,
        '\u{0009}'
            | '\u{000A}'
            | '\u{000B}'
            | '\u{000C}'
            | '\u{000D}'
            | '\u{0020}'
            | '\u{0085}'
            | '\u{00A0}'
            | '\u{1680}'
            | '\u{2000}'
            ..='\u{200A}' | '\u{2028}' | '\u{2029}' | '\u{202F}' | '\u{205F}' | '\u{3000}'
    )
}

/// Split text on runs of SPEC whitespace; drop empty parts.
pub fn tokenize(text: &str) -> alloc::vec::Vec<&str> {
    text.split(is_spec_whitespace)
        .filter(|t| !t.is_empty())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tokenize_basic() {
        assert_eq!(tokenize("a b  c\t\td\n"), vec!["a", "b", "c", "d"]);
    }

    #[test]
    fn test_tokenize_empty_and_whitespace_only() {
        assert!(tokenize("").is_empty());
        assert!(tokenize("   \t\n\u{00A0}").is_empty());
    }

    #[test]
    fn test_tokenize_unicode_whitespace() {
        // NBSP, ideographic space, NEL are in the set.
        assert_eq!(
            tokenize("a\u{00A0}b\u{3000}c\u{0085}d"),
            vec!["a", "b", "c", "d"]
        );
        // U+200B (ZWSP) and U+FEFF (BOM) are NOT in the set.
        assert_eq!(tokenize("a\u{200B}b"), vec!["a\u{200B}b"]);
        assert_eq!(tokenize("a\u{FEFF}b"), vec!["a\u{FEFF}b"]);
    }
}
