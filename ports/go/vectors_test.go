package lomboksimhash

// Vector tests: consume the ONE shared cross-language vectors file
// (vectors/lomboksimhash-vectors-v2.json), same as Rust/TS/Python/PHP.
// Comparisons are exact hex, never near-equality.

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"reflect"
	"testing"
)

const vectorsPath = "../../vectors/lomboksimhash-vectors-v2.json"

type vectorDoc struct {
	Schema string `json:"schema"`
	Cases  struct {
		Sha256 []struct {
			ID          string `json:"id"`
			Input       string `json:"input"`
			InputHex    string `json:"input_hex"`
			ExpectedHex string `json:"expected_hex"`
		} `json:"sha256"`
		Fnv1a64 []struct {
			ID          string `json:"id"`
			InputHex    string `json:"input_hex"`
			ExpectedHex string `json:"expected_hex"`
		} `json:"fnv1a64"`
		Shingle []struct {
			ID       string   `json:"id"`
			Input    string   `json:"input"`
			Mode     string   `json:"mode"`
			N        int      `json:"n"`
			Expected []string `json:"expected"`
		} `json:"shingle"`
		Simhash64 []struct {
			ID          string `json:"id"`
			Input       string `json:"input"`
			ExpectedHex string `json:"expected_hex"`
		} `json:"simhash64"`
		Simhash128 []struct {
			ID      string `json:"id"`
			Input   string `json:"input"`
			HiHex   string `json:"hi_hex"`
			LoHex   string `json:"lo_hex"`
			FullHex string `json:"hex"`
		} `json:"simhash128"`
		MinhashSignature []struct {
			ID           string   `json:"id"`
			Tokens       []string `json:"tokens"`
			NumPerm      int      `json:"num_perm"`
			SignatureHex []string `json:"signature_hex"`
		} `json:"minhash_signature"`
		MinhashJaccard []struct {
			ID              string   `json:"id"`
			SetA            []string `json:"set_a"`
			SetB            []string `json:"set_b"`
			NumPerm         int      `json:"num_perm"`
			ExpectedMatches int      `json:"expected_matches"`
		} `json:"minhash_jaccard"`
		LshBandhash []struct {
			ID             string   `json:"id"`
			BandValuesHex  []string `json:"band_values_hex"`
			ExpectedKeyHex string   `json:"expected_key_hex"`
		} `json:"lsh_bandhash"`
		LshIndex []struct {
			ID      string `json:"id"`
			Bands   int    `json:"bands"`
			Rows    int    `json:"rows"`
			Inserts []struct {
				DocID        string   `json:"doc_id"`
				SignatureHex []string `json:"signature_hex"`
			} `json:"inserts"`
			QueryHex []string `json:"query_hex"`
			Expected []string `json:"expected"`
			Remove   *struct {
				DocID        string   `json:"doc_id"`
				SignatureHex []string `json:"signature_hex"`
			} `json:"remove"`
			ExpectedAfterRemove []string `json:"expected_after_remove"`
		} `json:"lsh_index"`
	} `json:"cases"`
}

func loadVectors(t *testing.T) *vectorDoc {
	t.Helper()
	raw, err := os.ReadFile(vectorsPath)
	if err != nil {
		t.Fatalf("read vectors: %v", err)
	}
	var doc vectorDoc
	if err := json.Unmarshal(raw, &doc); err != nil {
		t.Fatalf("parse vectors: %v", err)
	}
	if doc.Schema != "lomboksimhash-vectors-v2" {
		t.Fatalf("unexpected schema %q", doc.Schema)
	}
	return &doc
}

func hexesToU64s(t *testing.T, hexes []string) []uint64 {
	t.Helper()
	out := make([]uint64, len(hexes))
	for i, h := range hexes {
		v, err := strconvParseU64(h)
		if err != nil {
			t.Fatalf("bad hex %q: %v", h, err)
		}
		out[i] = v
	}
	return out
}

func strconvParseU64(h string) (uint64, error) {
	var v uint64
	for i := 0; i < len(h); i++ {
		d := hexDigit(h[i])
		if d < 0 {
			return 0, fmt.Errorf("bad digit %q", h[i])
		}
		v = v<<4 | uint64(d)
	}
	return v, nil
}

func hexDigit(c byte) int {
	switch {
	case c >= '0' && c <= '9':
		return int(c - '0')
	case c >= 'a' && c <= 'f':
		return int(c-'a') + 10
	default:
		return -1
	}
}

func hexU64(v uint64) string {
	return fmt.Sprintf("%016x", v)
}

func TestVectorsSha256(t *testing.T) {
	doc := loadVectors(t)
	for _, c := range doc.Cases.Sha256 {
		data, err := hex.DecodeString(c.InputHex)
		if err != nil {
			t.Fatalf("case %s: bad hex: %v", c.ID, err)
		}
		if c.Input != "" && c.InputHex == "" {
			data = []byte(c.Input)
		}
		t.Run(c.ID, func(t *testing.T) {
			if got := SHA256(data); got != c.ExpectedHex {
				t.Errorf("got %s want %s", got, c.ExpectedHex)
			}
		})
	}
}

func TestVectorsFnv1a64(t *testing.T) {
	doc := loadVectors(t)
	for _, c := range doc.Cases.Fnv1a64 {
		data, _ := hex.DecodeString(c.InputHex)
		t.Run(c.ID, func(t *testing.T) {
			if got := hexU64(FNV1a64(data)); got != c.ExpectedHex {
				t.Errorf("got %s want %s", got, c.ExpectedHex)
			}
		})
	}
}

func TestVectorsShingle(t *testing.T) {
	doc := loadVectors(t)
	for _, c := range doc.Cases.Shingle {
		t.Run(c.ID, func(t *testing.T) {
			var got []string
			if c.Mode == "character" {
				got = CharShingles(c.Input, c.N)
			} else {
				got = WordShingles(c.Input, c.N)
			}
			if !reflect.DeepEqual(got, c.Expected) {
				t.Errorf("got %v want %v", got, c.Expected)
			}
		})
	}
}

func TestVectorsSimhash64(t *testing.T) {
	doc := loadVectors(t)
	for _, c := range doc.Cases.Simhash64 {
		t.Run(c.ID, func(t *testing.T) {
			got := hexU64(SimHash64Text(c.Input))
			if got != c.ExpectedHex {
				t.Errorf("got %s want %s", got, c.ExpectedHex)
			}
		})
	}
}

func TestVectorsSimhash128(t *testing.T) {
	doc := loadVectors(t)
	for _, c := range doc.Cases.Simhash128 {
		t.Run(c.ID, func(t *testing.T) {
			hi, lo := SimHash128Text(c.Input)
			if got := hexU64(hi); got != c.HiHex {
				t.Errorf("hi: got %s want %s", got, c.HiHex)
			}
			if got := hexU64(lo); got != c.LoHex {
				t.Errorf("lo: got %s want %s", got, c.LoHex)
			}
		})
	}
}

func TestVectorsMinhashSignature(t *testing.T) {
	doc := loadVectors(t)
	for _, c := range doc.Cases.MinhashSignature {
		t.Run(c.ID, func(t *testing.T) {
			mh := NewMinHasher(c.NumPerm)
			mh.AddTokens(c.Tokens)
			want := hexesToU64s(t, c.SignatureHex)
			if !reflect.DeepEqual(mh.Signature, want) {
				t.Errorf("signature mismatch")
				for i := range want {
					if mh.Signature[i] != want[i] {
						t.Errorf("  [%d] got %016x want %016x", i, mh.Signature[i], want[i])
					}
				}
			}
		})
	}
}

func TestVectorsMinhashJaccard(t *testing.T) {
	doc := loadVectors(t)
	for _, c := range doc.Cases.MinhashJaccard {
		t.Run(c.ID, func(t *testing.T) {
			a := NewMinHasher(c.NumPerm)
			b := NewMinHasher(c.NumPerm)
			a.AddTokens(c.SetA)
			b.AddTokens(c.SetB)
			matches := 0
			for i := range a.Signature {
				if a.Signature[i] == b.Signature[i] {
					matches++
				}
			}
			if matches != c.ExpectedMatches {
				t.Errorf("got %d matches want %d", matches, c.ExpectedMatches)
			}
		})
	}
}

func TestVectorsLshBandhash(t *testing.T) {
	doc := loadVectors(t)
	for _, c := range doc.Cases.LshBandhash {
		t.Run(c.ID, func(t *testing.T) {
			values := hexesToU64s(t, c.BandValuesHex)
			// bandHash is package-private: accessible from this same package.
			if got := hexU64(bandHash(values)); got != c.ExpectedKeyHex {
				t.Errorf("got %s want %s", got, c.ExpectedKeyHex)
			}
		})
	}
}

func TestVectorsLshIndex(t *testing.T) {
	doc := loadVectors(t)
	for _, c := range doc.Cases.LshIndex {
		t.Run(c.ID, func(t *testing.T) {
			idx := NewLshIndex(c.Bands, c.Rows)
			for _, ins := range c.Inserts {
				idx.Insert(ins.DocID, hexesToU64s(t, ins.SignatureHex))
			}
			got := idx.Query(hexesToU64s(t, c.QueryHex))
			if !reflect.DeepEqual(got, c.Expected) {
				t.Errorf("got %v want %v", got, c.Expected)
			}
			if c.Remove != nil {
				idx.Remove(c.Remove.DocID, hexesToU64s(t, c.Remove.SignatureHex))
				after := idx.Query(hexesToU64s(t, c.QueryHex))
				if !reflect.DeepEqual(after, c.ExpectedAfterRemove) {
					t.Errorf("after remove: got %v want %v", after, c.ExpectedAfterRemove)
				}
			}
		})
	}
}

// --- error-contract (panic message) tests: table-driven ---

func TestErrorContract(t *testing.T) {
	cases := []struct {
		name    string
		wantPnc string
		action  func()
	}{
		{
			name:    "minhash zero perm",
			wantPnc: "[ERR_MINHASH_PERM] num_perm must be > 0",
			action:  func() { NewMinHasher(0) },
		},
		{
			name:    "lsh zero bands",
			wantPnc: "[ERR_LSH_CONFIG] bands and rows must be > 0",
			action:  func() { NewLshIndex(0, 5) },
		},
		{
			name:    "lsh zero rows",
			wantPnc: "[ERR_LSH_CONFIG] bands and rows must be > 0",
			action:  func() { NewLshIndex(5, 0) },
		},
		{
			name:    "lsh insert wrong sig len",
			wantPnc: "[ERR_SIG_LEN] signature length must be bands * rows = 10",
			action: func() {
				idx := NewLshIndex(5, 2)
				idx.Insert("d", []uint64{1, 2, 3})
			},
		},
		{
			name:    "lsh query wrong sig len",
			wantPnc: "[ERR_SIG_LEN] signature length must be bands * rows = 10",
			action: func() {
				idx := NewLshIndex(5, 2)
				idx.Query([]uint64{1})
			},
		},
		{
			name:    "jaccard len mismatch",
			wantPnc: "[ERR_JACCARD_LEN] signatures must have same length",
			action: func() {
				JaccardEstimate([]uint64{1, 2}, []uint64{1})
			},
		},
		{
			name:    "jaccard empty",
			wantPnc: "[ERR_JACCARD_EMPTY] signatures must not be empty",
			action:  func() { JaccardEstimate(nil, nil) },
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			defer func() {
				r := recover()
				if r == nil {
					t.Fatalf("expected panic %q, got none", tc.wantPnc)
				}
				msg := fmt.Sprint(r)
				if msg != tc.wantPnc {
					t.Errorf("panic = %q, want %q", msg, tc.wantPnc)
				}
			}()
			tc.action()
		})
	}
}

// --- property-based (light) checks ---

func TestPropertyMinhashIdenticalSets(t *testing.T) {
	alphabet := []string{"a", "b", "c", "d", "e", "f", "g", "h", "你", "好"}
	seed := uint64(0x5DEECE66D)
	next := func(mod uint64) uint64 {
		seed = seed*6364136223846793005 + 1442695040888963407
		return (seed >> 33) % mod
	}
	for round := 0; round < 25; round++ {
		size := int(next(8)) + 1
		set := make([]string, 0, size)
		for i := 0; i < size; i++ {
			set = append(set, alphabet[next(uint64(len(alphabet)))])
		}
		perm := int(next(96)) + 32
		a := NewMinHasher(perm)
		b := NewMinHasher(perm)
		a.AddTokens(set)
		b.AddTokens(set)
		if got := JaccardEstimate(a.Signature, b.Signature); got != 1.0 {
			t.Fatalf("round %d: identical sets J=%v", round, got)
		}
	}
}

func TestPropertySimhash128LoMatches64(t *testing.T) {
	inputs := []string{
		"alpha beta gamma", "你好 世界", "héllo wörld", "single",
		"", "   ", "Rust, TypeScript, Go — satu kontrak bit-identical 🌍",
	}
	for _, in := range inputs {
		hi, lo := SimHash128Text(in)
		if lo != SimHash64Text(in) {
			t.Errorf("input %q: simhash128.lo != simhash64", in)
		}
		if Hamming128(hi, lo, hi, lo) != 0 {
			t.Errorf("input %q: hamming(x,x) != 0", in)
		}
	}
}

// Universal hash reference check with big.Int for a sample of the actual
// permutation family (guards the Mersenne reduction).
func TestUniversalHashAgainstBig(t *testing.T) {
	mersenne := new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), 61), big.NewInt(1))
	mh := NewMinHasher(64)
	_ = mh
	params := generateHashParams(64)
	tokens := []string{"the", "quick", "brown", "fox", "你好", "世界"}
	for i, p := range params {
		a := new(big.Int).SetUint64(p.a)
		b := new(big.Int).SetUint64(p.b)
		for _, tok := range tokens {
			x := new(big.Int).SetUint64(FNV1a64([]byte(tok)))
			xMod := new(big.Int).Mod(x, mersenne)
			want := new(big.Int).Mul(a, xMod)
			want.Add(want, b)
			want.Mod(want, mersenne)
			got := universalHash(p.a, p.b, FNV1a64([]byte(tok)))
			if got != want.Uint64() {
				t.Errorf("perm %d token %q: got %d want %s", i, tok, got, want.String())
			}
		}
	}
}

func TestTokenizeSpecSet(t *testing.T) {
	got := Tokenize("a\u00a0b\u3000c\u000bd")
	want := []string{"a", "b", "c", "d"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %v want %v", got, want)
	}
	// ZWSP / BOM are NOT in the SPEC set
	if got := Tokenize("a\u200bb"); len(got) != 1 || got[0] != "a\u200bb" {
		t.Errorf("ZWSP must not split: %q", got)
	}
	if got := Tokenize(" \t\n"); len(got) != 0 {
		t.Errorf("ws-only must be empty: %q", got)
	}
}
