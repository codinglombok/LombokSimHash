// Package lomboksimhash provides locality-sensitive hashing for near-duplicate
// document detection. SimHash, MinHash, LSH, SHA-256, and shingling.
//
// Part of LombokRAGFrameworks. Zero external dependencies.
// License: Apache-2.0
package lomboksimhash

import (
	"encoding/binary"
	"fmt"
	"math"
	"math/bits"
	"sort"
	"strings"
)

// ============================================================
// SHA-256 (FIPS 180-4)
// ============================================================

var kSHA = [64]uint32{
	0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
	0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
	0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
	0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
	0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
	0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
	0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
	0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
	0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
}

var hInit = [8]uint32{
	0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
	0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
}

func sha256compress(state *[8]uint32, block []byte) {
	var w [64]uint32
	for i := 0; i < 16; i++ {
		w[i] = binary.BigEndian.Uint32(block[i*4 : i*4+4])
	}
	for i := 16; i < 64; i++ {
		s0 := bits.RotateLeft32(w[i-15], -7) ^ bits.RotateLeft32(w[i-15], -18) ^ (w[i-15] >> 3)
		s1 := bits.RotateLeft32(w[i-2], -17) ^ bits.RotateLeft32(w[i-2], -19) ^ (w[i-2] >> 10)
		w[i] = w[i-16] + s0 + w[i-7] + s1
	}

	a, b, c, d, e, f, g, h := state[0], state[1], state[2], state[3], state[4], state[5], state[6], state[7]

	for i := 0; i < 64; i++ {
		s1 := bits.RotateLeft32(e, -6) ^ bits.RotateLeft32(e, -11) ^ bits.RotateLeft32(e, -25)
		ch := (e & f) ^ (^e & g)
		temp1 := h + s1 + ch + kSHA[i] + w[i]
		s0 := bits.RotateLeft32(a, -2) ^ bits.RotateLeft32(a, -13) ^ bits.RotateLeft32(a, -22)
		maj := (a & b) ^ (a & c) ^ (b & c)
		temp2 := s0 + maj

		h = g
		g = f
		f = e
		e = d + temp1
		d = c
		c = b
		b = a
		a = temp1 + temp2
	}

	state[0] += a
	state[1] += b
	state[2] += c
	state[3] += d
	state[4] += e
	state[5] += f
	state[6] += g
	state[7] += h
}

// SHA256 computes the SHA-256 hash of data and returns the hex string.
func SHA256(data []byte) string {
	state := hInit

	bitLen := uint64(len(data)) * 8
	padded := make([]byte, len(data))
	copy(padded, data)
	padded = append(padded, 0x80)
	for len(padded)%64 != 56 {
		padded = append(padded, 0x00)
	}
	lenBytes := make([]byte, 8)
	binary.BigEndian.PutUint64(lenBytes, bitLen)
	padded = append(padded, lenBytes...)

	for i := 0; i < len(padded); i += 64 {
		sha256compress(&state, padded[i:i+64])
	}

	return fmt.Sprintf("%08x%08x%08x%08x%08x%08x%08x%08x",
		state[0], state[1], state[2], state[3],
		state[4], state[5], state[6], state[7])
}

// ============================================================
// FNV-1a 64-bit
// ============================================================

const (
	fnv64Offset = uint64(0xcbf29ce484222325)
	fnv64Prime  = uint64(0x100000001b3)
)

// FNV1a64 computes the FNV-1a 64-bit hash.
func FNV1a64(data []byte) uint64 {
	h := fnv64Offset
	for _, b := range data {
		h ^= uint64(b)
		h *= fnv64Prime
	}
	return h
}

// ============================================================
// Tokenization — exact SPEC whitespace contract
// ============================================================

// Tokenize splits text on runs of the SPEC whitespace set (Unicode
// White_Space property, 25 code points) and drops empty parts.
// strings.Fields implements exactly that set.
func Tokenize(text string) []string {
	return strings.Fields(text)
}

// ============================================================
// Shingling
// ============================================================

// CharShingles returns sorted unique character n-grams.
func CharShingles(text string, n int) []string {
	runes := []rune(text)
	set := make(map[string]struct{})
	for i := 0; i <= len(runes)-n; i++ {
		set[string(runes[i:i+n])] = struct{}{}
	}
	result := make([]string, 0, len(set))
	for s := range set {
		result = append(result, s)
	}
	sort.Strings(result)
	return result
}

// WordShingles returns sorted unique word n-grams.
func WordShingles(text string, n int) []string {
	words := strings.Fields(text)
	set := make(map[string]struct{})
	for i := 0; i <= len(words)-n; i++ {
		set[strings.Join(words[i:i+n], " ")] = struct{}{}
	}
	result := make([]string, 0, len(set))
	for s := range set {
		result = append(result, s)
	}
	sort.Strings(result)
	return result
}

// ============================================================
// SimHash
// ============================================================

// SimHash64 computes 64-bit SimHash from tokens.
func SimHash64(tokens []string) uint64 {
	var v [64]int
	for _, token := range tokens {
		h := FNV1a64([]byte(token))
		for i := 0; i < 64; i++ {
			if (h>>uint(i))&1 == 1 {
				v[i]++
			} else {
				v[i]--
			}
		}
	}
	var result uint64
	for i := 0; i < 64; i++ {
		if v[i] > 0 {
			result |= 1 << uint(i)
		}
	}
	return result
}

// SimHash64Text tokenizes by whitespace and computes SimHash64.
func SimHash64Text(text string) uint64 {
	return SimHash64(strings.Fields(text))
}

// Hamming64 returns the Hamming distance between two 64-bit values.
func Hamming64(a, b uint64) int {
	return bits.OnesCount64(a ^ b)
}

// SimHash128 computes 128-bit SimHash from tokens.
// lo accumulates FNV1a64(utf8(token)) bits; hi accumulates
// FNV1a64(utf8(token) || 0xFF) bits.
func SimHash128(tokens []string) (hi, lo uint64) {
	var v [128]int
	for _, token := range tokens {
		h1 := FNV1a64([]byte(token))
		h2 := FNV1a64(append([]byte(token), 0xFF))
		for i := 0; i < 64; i++ {
			if (h1>>uint(i))&1 == 1 {
				v[i]++
			} else {
				v[i]--
			}
			if (h2>>uint(i))&1 == 1 {
				v[64+i]++
			} else {
				v[64+i]--
			}
		}
	}
	for i := 0; i < 64; i++ {
		if v[i] > 0 {
			lo |= 1 << uint(i)
		}
		if v[64+i] > 0 {
			hi |= 1 << uint(i)
		}
	}
	return hi, lo
}

// SimHash128Text tokenizes by the SPEC whitespace set and computes SimHash128.
func SimHash128Text(text string) (hi, lo uint64) {
	return SimHash128(Tokenize(text))
}

// Hamming128 returns the Hamming distance between two 128-bit (hi, lo) pairs.
func Hamming128(aHi, aLo, bHi, bLo uint64) int {
	return bits.OnesCount64(aHi^bHi) + bits.OnesCount64(aLo^bLo)
}

// ============================================================
// MinHash
// ============================================================

const (
	mersenne61 = uint64((1 << 61) - 1)
	lcgSeed    = uint64(0x517cc1b727220a95)
	lcgMul     = uint64(6364136223846793005)
	lcgInc     = uint64(1442695040888963407)
)

type hashParam struct{ a, b uint64 }

func generateHashParams(numPerm int) []hashParam {
	state := lcgSeed
	params := make([]hashParam, numPerm)
	for i := 0; i < numPerm; i++ {
		state = state*lcgMul + lcgInc
		a := state % mersenne61
		if a == 0 {
			a = 1
		}
		state = state*lcgMul + lcgInc
		b := state % mersenne61
		params[i] = hashParam{a, b}
	}
	return params
}

func universalHash(a, b, x uint64) uint64 {
	xMod := x % mersenne61
	// Use 128-bit multiply via two 64-bit ops
	hi, lo := bits.Mul64(a, xMod)
	// Add b
	lo, carry := bits.Add64(lo, b, 0)
	hi += carry
	// Mod mersenne61: (hi * 2^64 + lo) mod (2^61 - 1)
	// = (hi * (2^61 * 8) + lo) mod (2^61 - 1)
	// = (hi * 8 + lo_hi_3bits) * 2^61 + lo_low_61bits) mod (2^61 - 1)
	// Simplified: reduce by splitting
	result := (hi << 3) | (lo >> 61)
	result += lo & mersenne61
	if result >= mersenne61 {
		result -= mersenne61
	}
	return result
}

// MinHasher generates MinHash signatures.
type MinHasher struct {
	NumPerm   int
	Signature []uint64
	params    []hashParam
}

// NewMinHasher creates a MinHasher with numPerm permutations.
//
// It panics with [ERR_MINHASH_PERM] when numPerm == 0.
func NewMinHasher(numPerm int) *MinHasher {
	if numPerm < 1 {
		panic("[ERR_MINHASH_PERM] num_perm must be > 0")
	}
	sig := make([]uint64, numPerm)
	for i := range sig {
		sig[i] = ^uint64(0)
	}
	return &MinHasher{
		NumPerm:   numPerm,
		Signature: sig,
		params:    generateHashParams(numPerm),
	}
}

// Add adds a token to the MinHash signature.
func (m *MinHasher) Add(token string) {
	h := FNV1a64([]byte(token))
	for i := 0; i < m.NumPerm; i++ {
		val := universalHash(m.params[i].a, m.params[i].b, h)
		if val < m.Signature[i] {
			m.Signature[i] = val
		}
	}
}

// AddTokens adds multiple tokens.
func (m *MinHasher) AddTokens(tokens []string) {
	for _, t := range tokens {
		m.Add(t)
	}
}

// JaccardEstimate estimates Jaccard similarity between two signatures.
//
// It panics with [ERR_JACCARD_LEN] on length mismatch and
// [ERR_JACCARD_EMPTY] on empty signatures.
func JaccardEstimate(sigA, sigB []uint64) float64 {
	if len(sigA) != len(sigB) {
		panic("[ERR_JACCARD_LEN] signatures must have same length")
	}
	if len(sigA) == 0 {
		panic("[ERR_JACCARD_EMPTY] signatures must not be empty")
	}
	matches := 0
	for i := range sigA {
		if sigA[i] == sigB[i] {
			matches++
		}
	}
	return float64(matches) / float64(len(sigA))
}

// ============================================================
// LSH Index
// ============================================================

// LshIndex is a locality-sensitive hash index using band+row technique.
type LshIndex struct {
	Bands   int
	Rows    int
	buckets []map[uint64][]string
}

// NewLshIndex creates a new LSH index.
//
// It panics with [ERR_LSH_CONFIG] when bands == 0 or rows == 0.
func NewLshIndex(bands, rows int) *LshIndex {
	if bands < 1 || rows < 1 {
		panic("[ERR_LSH_CONFIG] bands and rows must be > 0")
	}
	buckets := make([]map[uint64][]string, bands)
	for i := range buckets {
		buckets[i] = make(map[uint64][]string)
	}
	return &LshIndex{Bands: bands, Rows: rows, buckets: buckets}
}

// SignatureLen returns the required MinHash signature length.
func (l *LshIndex) SignatureLen() int {
	return l.Bands * l.Rows
}

// Threshold returns the approximate Jaccard threshold.
func (l *LshIndex) Threshold() float64 {
	return math.Pow(1.0/float64(l.Bands), 1.0/float64(l.Rows))
}

func bandHash(vals []uint64) uint64 {
	h := fnv64Offset
	for _, val := range vals {
		var buf [8]byte
		binary.LittleEndian.PutUint64(buf[:], val)
		for _, b := range buf {
			h ^= uint64(b)
			h *= fnv64Prime
		}
	}
	return h
}

// Insert adds a document's MinHash signature.
//
// It panics with [ERR_SIG_LEN] when the signature length is not bands*rows.
func (l *LshIndex) Insert(docID string, sig []uint64) {
	l.assertSigLen(sig)
	for b := 0; b < l.Bands; b++ {
		start := b * l.Rows
		key := bandHash(sig[start : start+l.Rows])
		l.buckets[b][key] = append(l.buckets[b][key], docID)
	}
}

// Query returns candidate near-duplicates, deduplicated and sorted ascending.
//
// It panics with [ERR_SIG_LEN] when the signature length is not bands*rows.
func (l *LshIndex) Query(sig []uint64) []string {
	l.assertSigLen(sig)
	seen := make(map[string]struct{})
	for b := 0; b < l.Bands; b++ {
		start := b * l.Rows
		key := bandHash(sig[start : start+l.Rows])
		for _, d := range l.buckets[b][key] {
			seen[d] = struct{}{}
		}
	}
	result := make([]string, 0, len(seen))
	for d := range seen {
		result = append(result, d)
	}
	sort.Strings(result)
	return result
}

// Remove removes a document from every band bucket touched by the signature.
//
// It panics with [ERR_SIG_LEN] when the signature length is not bands*rows.
func (l *LshIndex) Remove(docID string, sig []uint64) {
	l.assertSigLen(sig)
	for b := 0; b < l.Bands; b++ {
		start := b * l.Rows
		key := bandHash(sig[start : start+l.Rows])
		docs := l.buckets[b][key]
		filtered := docs[:0]
		for _, d := range docs {
			if d != docID {
				filtered = append(filtered, d)
			}
		}
		l.buckets[b][key] = filtered
	}
}

func (l *LshIndex) assertSigLen(sig []uint64) {
	if len(sig) != l.SignatureLen() {
		panic(fmt.Sprintf("[ERR_SIG_LEN] signature length must be bands * rows = %d", l.SignatureLen()))
	}
}
