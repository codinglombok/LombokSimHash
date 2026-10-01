package lomboksimhash

import (
	"fmt"
	"math"
	"testing"
)

func TestSHA256Empty(t *testing.T) {
	got := SHA256([]byte(""))
	want := "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
	if got != want {
		t.Errorf("SHA256 empty: got %s, want %s", got, want)
	}
}

func TestSHA256Hello(t *testing.T) {
	got := SHA256([]byte("hello"))
	want := "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
	if got != want {
		t.Errorf("SHA256 hello: got %s, want %s", got, want)
	}
}

func TestSHA256Fox(t *testing.T) {
	got := SHA256([]byte("the quick brown fox jumps over the lazy dog"))
	want := "05c6e08f1d9fdafa03147fcb8f82f124c76d2f70e3d989dc8aadb5e7d7450bec"
	if got != want {
		t.Errorf("SHA256 fox: got %s, want %s", got, want)
	}
}

func TestFNV1a64Empty(t *testing.T) {
	got := fmt.Sprintf("%x", FNV1a64([]byte("")))
	if got != "cbf29ce484222325" {
		t.Errorf("FNV1a64 empty: got %s", got)
	}
}

func TestFNV1a64Hello(t *testing.T) {
	got := fmt.Sprintf("%x", FNV1a64([]byte("hello")))
	if got != "a430d84680aabd0b" {
		t.Errorf("FNV1a64 hello: got %s", got)
	}
}

func TestCharShingles(t *testing.T) {
	got := CharShingles("abcde", 3)
	want := []string{"abc", "bcd", "cde"}
	if len(got) != len(want) {
		t.Fatalf("CharShingles: got %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("CharShingles[%d]: got %s, want %s", i, got[i], want[i])
		}
	}
}

func TestWordShingles(t *testing.T) {
	got := WordShingles("the quick brown fox", 2)
	want := []string{"brown fox", "quick brown", "the quick"}
	if len(got) != len(want) {
		t.Fatalf("WordShingles: got %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("WordShingles[%d]: got %s, want %s", i, got[i], want[i])
		}
	}
}

func TestSimHash64Fox(t *testing.T) {
	got := fmt.Sprintf("%016x", SimHash64Text("the quick brown fox jumps over the lazy dog"))
	if got != "cab7991c5475edee" {
		t.Errorf("SimHash64 fox: got %s", got)
	}
}

func TestSimHash64Cat(t *testing.T) {
	got := fmt.Sprintf("%016x", SimHash64Text("the quick brown cat jumps over the lazy dog"))
	if got != "c2e7991c1465e56f" {
		t.Errorf("SimHash64 cat: got %s", got)
	}
}

func TestHamming64FoxCat(t *testing.T) {
	fox := SimHash64Text("the quick brown fox jumps over the lazy dog")
	cat := SimHash64Text("the quick brown cat jumps over the lazy dog")
	if Hamming64(fox, cat) != 8 {
		t.Errorf("Hamming fox-cat: got %d, want 8", Hamming64(fox, cat))
	}
}

func TestSimHash64Deterministic(t *testing.T) {
	a := SimHash64Text("test determinism")
	b := SimHash64Text("test determinism")
	if a != b {
		t.Error("SimHash64 not deterministic")
	}
}

func TestMinHashIdentical(t *testing.T) {
	a := NewMinHasher(128)
	b := NewMinHasher(128)
	tokens := []string{"the", "quick", "brown", "fox"}
	a.AddTokens(tokens)
	b.AddTokens(tokens)
	j := JaccardEstimate(a.Signature, b.Signature)
	if j != 1.0 {
		t.Errorf("MinHash identical: got J=%f, want 1.0", j)
	}
}

func TestMinHashDisjoint(t *testing.T) {
	a := NewMinHasher(128)
	b := NewMinHasher(128)
	a.AddTokens([]string{"alpha", "beta", "gamma"})
	b.AddTokens([]string{"delta", "epsilon", "zeta"})
	j := JaccardEstimate(a.Signature, b.Signature)
	if j >= 0.2 {
		t.Errorf("MinHash disjoint: got J=%f, want < 0.2", j)
	}
}

func TestMinHashOverlapping(t *testing.T) {
	a := NewMinHasher(128)
	b := NewMinHasher(128)
	a.AddTokens([]string{"a", "b", "c", "d"})
	b.AddTokens([]string{"c", "d", "e", "f"})
	j := JaccardEstimate(a.Signature, b.Signature)
	if j < 0.1 || j > 0.6 {
		t.Errorf("MinHash overlapping: got J=%f, want ≈0.33", j)
	}
}

func TestMinHashDeterministic(t *testing.T) {
	a := NewMinHasher(64)
	b := NewMinHasher(64)
	a.AddTokens([]string{"hello", "world"})
	b.AddTokens([]string{"hello", "world"})
	for i := range a.Signature {
		if a.Signature[i] != b.Signature[i] {
			t.Fatalf("MinHash not deterministic at index %d", i)
		}
	}
}

func TestLshThreshold(t *testing.T) {
	idx := NewLshIndex(20, 5)
	th := idx.Threshold()
	if math.Abs(th-0.5493) > 0.01 {
		t.Errorf("LSH threshold: got %f, want ≈0.5493", th)
	}
}

func TestLshInsertQuery(t *testing.T) {
	idx := NewLshIndex(20, 5)
	mh := NewMinHasher(100)
	mh.AddTokens([]string{"the", "quick", "brown", "fox"})
	idx.Insert("doc1", mh.Signature)
	cands := idx.Query(mh.Signature)
	found := false
	for _, c := range cands {
		if c == "doc1" {
			found = true
		}
	}
	if !found {
		t.Error("LSH query should find doc1")
	}
}

func TestLshRemove(t *testing.T) {
	idx := NewLshIndex(20, 5)
	mh := NewMinHasher(100)
	mh.AddTokens([]string{"hello", "world"})
	sig := make([]uint64, len(mh.Signature))
	copy(sig, mh.Signature)
	idx.Insert("doc1", sig)
	idx.Remove("doc1", sig)
	cands := idx.Query(sig)
	for _, c := range cands {
		if c == "doc1" {
			t.Error("LSH remove should have removed doc1")
		}
	}
}
