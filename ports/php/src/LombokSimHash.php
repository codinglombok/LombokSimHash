<?php

/**
 * LombokSimHash — PHP Port (core hash/fingerprint functions).
 *
 * Near-duplicate document detection for RAG pipelines.
 * Uses GMP for 64-bit math and the built-in hash() for SHA-256 (FIPS 180-4).
 *
 * Behavior is pinned by docs/SPEC_LombokSimHash_0.1.0.md and the shared
 * cross-language vectors (vectors/lomboksimhash-vectors-v2.json).
 *
 * Part of LombokRAGFrameworks (Lombok Ecosystem).
 * @license Apache-2.0
 */

namespace CodingLombok\LombokSimHash;

final class LombokSimHash
{
    // FNV-1a 64-bit constants
    private const FNV64_OFFSET = '14695981039346656037'; // 0xcbf29ce484222325
    private const FNV64_PRIME  = '1099511628211';        // 0x100000001b3

    // LCG constants (deterministic permutation family)
    private const LCG_SEED = '5871781006564002453';      // 0x517cc1b727220a95
    private const LCG_MUL  = '6364136223846793005';
    private const LCG_INC  = '1442695040888963407';

    // 2^64 - 1 (MinHash initial signature value), 2^61 - 1 (Mersenne prime)
    private const MASK64       = '18446744073709551615';
    private const MERSENNE_61  = '2305843009213693951';

    private function __construct()
    {
    }

    // ============================================================
    // SHA-256 (FIPS 180-4)
    // ============================================================

    /**
     * Compute SHA-256 of the input string (bytes). Returns lowercase hex.
     */
    public static function sha256(string $data): string
    {
        return hash('sha256', $data);
    }

    // ============================================================
    // FNV-1a 64-bit
    // ============================================================

    /**
     * FNV-1a 64-bit hash of the input bytes.
     */
    public static function fnv1a64(string $data): \GMP
    {
        $h = gmp_init(self::FNV64_OFFSET);
        $prime = gmp_init(self::FNV64_PRIME);
        $mask = gmp_init(self::MASK64);
        $len = strlen($data);
        for ($i = 0; $i < $len; $i++) {
            $h = gmp_xor($h, gmp_init(ord($data[$i])));
            $h = gmp_and(gmp_mul($h, $prime), $mask);
        }
        return $h;
    }

    // ============================================================
    // Shingling
    // ============================================================

    /**
     * Sorted unique character n-grams (Unicode code points, not bytes).
     *
     * @return list<string>
     */
    public static function charShingles(string $text, int $n): array
    {
        self::assertShingleN($n);
        $chars = mb_str_split($text, 1, 'UTF-8');
        if ($chars === false) {
            $chars = [];
        }
        $set = [];
        $count = count($chars);
        for ($i = 0; $i + $n <= $count; $i++) {
            $shingle = implode('', array_slice($chars, $i, $n));
            $set[$shingle] = true;
        }
        $result = array_keys($set);
        sort($result, SORT_STRING);
        return $result;
    }

    /**
     * Sorted unique word n-grams (tokens split on the SPEC whitespace set).
     *
     * @return list<string>
     */
    public static function wordShingles(string $text, int $n): array
    {
        self::assertShingleN($n);
        $words = self::tokenize($text);
        $set = [];
        $count = count($words);
        for ($i = 0; $i + $n <= $count; $i++) {
            $shingle = implode(' ', array_slice($words, $i, $n));
            $set[$shingle] = true;
        }
        $result = array_keys($set);
        sort($result, SORT_STRING);
        return $result;
    }

    // ============================================================
    // SimHash
    // ============================================================

    /**
     * 64-bit SimHash from tokens.
     */
    public static function simhash64(array $tokens): \GMP
    {
        /** @var list<int> $v */
        $v = array_fill(0, 64, 0);
        foreach ($tokens as $token) {
            $h = self::fnv1a64((string) $token);
            for ($i = 0; $i < 64; $i++) {
                if (gmp_testbit($h, $i)) {
                    $v[$i]++;
                } else {
                    $v[$i]--;
                }
            }
        }
        $result = gmp_init(0);
        for ($i = 0; $i < 64; $i++) {
            if ($v[$i] > 0) {
                gmp_setbit($result, $i);
            }
        }
        return $result;
    }

    /**
     * Tokenize by the SPEC whitespace set and compute simhash64.
     */
    public static function simhash64Text(string $text): \GMP
    {
        return self::simhash64(self::tokenize($text));
    }

    /**
     * 128-bit SimHash from tokens. Returns [hi, lo] as GMP values.
     *
     * @return array{\GMP, \GMP}
     */
    public static function simhash128(array $tokens): array
    {
        /** @var list<int> $v */
        $v = array_fill(0, 128, 0);
        foreach ($tokens as $token) {
            $bytes = (string) $token;
            $h1 = self::fnv1a64($bytes);
            $h2 = self::fnv1a64($bytes . "\xff");
            for ($i = 0; $i < 64; $i++) {
                if (gmp_testbit($h1, $i)) {
                    $v[$i]++;
                } else {
                    $v[$i]--;
                }
                if (gmp_testbit($h2, $i)) {
                    $v[64 + $i]++;
                } else {
                    $v[64 + $i]--;
                }
            }
        }
        $lo = gmp_init(0);
        $hi = gmp_init(0);
        for ($i = 0; $i < 64; $i++) {
            if ($v[$i] > 0) {
                gmp_setbit($lo, $i);
            }
            if ($v[64 + $i] > 0) {
                gmp_setbit($hi, $i);
            }
        }
        return [$hi, $lo];
    }

    /**
     * Tokenize by the SPEC whitespace set and compute simhash128.
     *
     * @return array{\GMP, \GMP}
     */
    public static function simhash128Text(string $text): array
    {
        return self::simhash128(self::tokenize($text));
    }

    /**
     * Hamming distance between two 64-bit GMP values.
     */
    public static function hamming64(\GMP $a, \GMP $b): int
    {
        return gmp_popcount(gmp_xor($a, $b));
    }

    /**
     * Hamming distance between two 128-bit values given as [hi, lo].
     *
     * @param array{\GMP, \GMP} $a
     * @param array{\GMP, \GMP} $b
     */
    public static function hamming128(array $a, array $b): int
    {
        return gmp_popcount(gmp_xor($a[0], $b[0]))
            + gmp_popcount(gmp_xor($a[1], $b[1]));
    }

    // ============================================================
    // MinHash
    // ============================================================

    /**
     * Deterministic (a, b) pairs via LCG; a in [1, p-1], b in [0, p-1].
     *
     * @return list<array{\GMP, \GMP}>
     */
    private static function generateHashParams(int $numPerm): array
    {
        $mask = gmp_init(self::MASK64);
        $mersenne = gmp_init(self::MERSENNE_61);
        $state = gmp_init(self::LCG_SEED);
        $mul = gmp_init(self::LCG_MUL);
        $inc = gmp_init(self::LCG_INC);
        $one = gmp_init(1);

        $params = [];
        for ($i = 0; $i < $numPerm; $i++) {
            $state = gmp_and(gmp_add(gmp_mul($state, $mul), $inc), $mask);
            $a = gmp_mod($state, $mersenne);
            if (gmp_cmp($a, 0) === 0) {
                $a = $one;
            }
            $state = gmp_and(gmp_add(gmp_mul($state, $mul), $inc), $mask);
            $b = gmp_mod($state, $mersenne);
            $params[] = [$a, $b];
        }
        return $params;
    }

    /**
     * Universal hash: (a * (x mod p) + b) mod p, p = 2^61 - 1.
     */
    private static function universalHash(\GMP $a, \GMP $b, \GMP $x): \GMP
    {
        $mersenne = gmp_init(self::MERSENNE_61);
        $xMod = gmp_mod($x, $mersenne);
        return gmp_mod(gmp_add(gmp_mul($a, $xMod), $b), $mersenne);
    }

    /**
     * MinHash signature for a token set. Signature[i] starts at 2^64 - 1.
     *
     * @param list<string> $tokens
     * @return list<\GMP>
     */
    public static function minhash(array $tokens, int $numPerm = 128): array
    {
        self::assertNumPerm($numPerm);
        $params = self::generateHashParams($numPerm);
        $mask = gmp_init(self::MASK64);
        /** @var list<\GMP> $signature */
        $signature = array_fill(0, $numPerm, $mask);

        foreach ($tokens as $token) {
            $h = self::fnv1a64($token);
            for ($i = 0; $i < $numPerm; $i++) {
                [$a, $b] = $params[$i];
                $val = self::universalHash($a, $b, $h);
                if (gmp_cmp($val, $signature[$i]) < 0) {
                    $signature[$i] = $val;
                }
            }
        }
        return $signature;
    }

    /**
     * Estimate Jaccard similarity from two MinHash signatures.
     *
     * @param list<\GMP> $sigA
     * @param list<\GMP> $sigB
     */
    public static function jaccardEstimate(array $sigA, array $sigB): float
    {
        if (count($sigA) !== count($sigB)) {
            throw new \InvalidArgumentException(
                '[ERR_JACCARD_LEN] signatures must have same length'
            );
        }
        if (count($sigA) === 0) {
            throw new \InvalidArgumentException(
                '[ERR_JACCARD_EMPTY] signatures must not be empty'
            );
        }
        $matches = 0;
        $n = count($sigA);
        for ($i = 0; $i < $n; $i++) {
            if (gmp_cmp($sigA[$i], $sigB[$i]) === 0) {
                $matches++;
            }
        }
        return $matches / $n;
    }

    // ============================================================
    // Internal
    // ============================================================

    private static function assertShingleN(int $n): void
    {
        if ($n < 1) {
            throw new \InvalidArgumentException('[ERR_SHINGLE_N] shingle size must be > 0');
        }
    }

    private static function assertNumPerm(int $numPerm): void
    {
        if ($numPerm < 1) {
            throw new \InvalidArgumentException('[ERR_MINHASH_PERM] num_perm must be > 0');
        }
    }

    /**
     * Tokenize on runs of the SPEC whitespace set (Unicode White_Space).
     *
     * @return list<string>
     */
    private static function tokenize(string $text): array
    {
        $parts = preg_split(
            '/[\t\n\x0B\x0C\r \x{0085}\x{00A0}\x{1680}\x{2000}-\x{200A}\x{2028}\x{2029}\x{202F}\x{205F}\x{3000}]+/u',
            $text,
            -1,
            PREG_SPLIT_NO_EMPTY
        );
        if ($parts === false) {
            return [];
        }
        return $parts;
    }
}
