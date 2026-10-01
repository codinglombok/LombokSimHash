<?php
/**
 * LombokSimHash — PHP Port
 * Near-duplicate document detection for RAG pipelines.
 * Uses GMP for 64-bit math, built-in hash() for SHA-256.
 *
 * Part of LombokRAGFrameworks.
 * @license Apache-2.0
 */

namespace CodingLombok\LombokSimHash;

class LombokSimHash
{
    // FNV-1a 64-bit constants
    private const FNV64_OFFSET = '14695981039346656037'; // 0xcbf29ce484222325
    private const FNV64_PRIME  = '1099511628211';        // 0x100000001b3

    // LCG constants
    private const LCG_SEED = '5871781006564002453';      // 0x517cc1b727220a95
    private const LCG_MUL  = '6364136223846793005';
    private const LCG_INC  = '1442695040888963407';

    // Mersenne prime 2^61 - 1
    private const MERSENNE_61 = '2305843009213693951';

    // ============================================================
    // SHA-256
    // ============================================================

    /**
     * Compute SHA-256 hash. Returns hex string.
     */
    public static function sha256(string $data): string
    {
        return hash('sha256', $data);
    }

    // ============================================================
    // FNV-1a 64-bit
    // ============================================================

    /**
     * FNV-1a 64-bit hash using GMP.
     */
    public static function fnv1a64(string $data): \GMP
    {
        $h = gmp_init(self::FNV64_OFFSET);
        $prime = gmp_init(self::FNV64_PRIME);
        $mask = gmp_sub(gmp_pow(2, 64), 1);

        for ($i = 0; $i < strlen($data); $i++) {
            $h = gmp_xor($h, gmp_init(ord($data[$i])));
            $h = gmp_and(gmp_mul($h, $prime), $mask);
        }
        return $h;
    }

    // ============================================================
    // Shingling
    // ============================================================

    /**
     * Generate character n-gram shingles.
     */
    public static function charShingles(string $text, int $n): array
    {
        $chars = mb_str_split($text);
        $set = [];
        for ($i = 0; $i <= count($chars) - $n; $i++) {
            $shingle = implode('', array_slice($chars, $i, $n));
            $set[$shingle] = true;
        }
        $result = array_keys($set);
        sort($result);
        return $result;
    }

    /**
     * Generate word n-gram shingles.
     */
    public static function wordShingles(string $text, int $n): array
    {
        $words = preg_split('/\s+/', trim($text), -1, PREG_SPLIT_NO_EMPTY);
        $set = [];
        for ($i = 0; $i <= count($words) - $n; $i++) {
            $shingle = implode(' ', array_slice($words, $i, $n));
            $set[$shingle] = true;
        }
        $result = array_keys($set);
        sort($result);
        return $result;
    }

    // ============================================================
    // SimHash
    // ============================================================

    /**
     * Compute 64-bit SimHash from tokens.
     */
    public static function simhash64(array $tokens): \GMP
    {
        $v = array_fill(0, 64, 0);
        foreach ($tokens as $token) {
            $h = self::fnv1a64($token);
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
     * Tokenize by whitespace and compute simhash64.
     */
    public static function simhash64Text(string $text): \GMP
    {
        $tokens = preg_split('/\s+/', trim($text), -1, PREG_SPLIT_NO_EMPTY);
        return self::simhash64($tokens);
    }

    /**
     * Hamming distance between two 64-bit GMP values.
     */
    public static function hamming64(\GMP $a, \GMP $b): int
    {
        return gmp_popcount(gmp_xor($a, $b));
    }

    // ============================================================
    // MinHash
    // ============================================================

    private static function generateHashParams(int $numPerm): array
    {
        $mask = gmp_sub(gmp_pow(2, 64), 1);
        $mersenne = gmp_init(self::MERSENNE_61);
        $state = gmp_init(self::LCG_SEED);
        $mul = gmp_init(self::LCG_MUL);
        $inc = gmp_init(self::LCG_INC);

        $params = [];
        for ($i = 0; $i < $numPerm; $i++) {
            $state = gmp_and(gmp_add(gmp_mul($state, $mul), $inc), $mask);
            $a = gmp_mod($state, $mersenne);
            if (gmp_cmp($a, 0) === 0) $a = gmp_init(1);

            $state = gmp_and(gmp_add(gmp_mul($state, $mul), $inc), $mask);
            $b = gmp_mod($state, $mersenne);

            $params[] = [$a, $b];
        }
        return $params;
    }

    private static function universalHash(\GMP $a, \GMP $b, \GMP $x): \GMP
    {
        $mersenne = gmp_init(self::MERSENNE_61);
        $xMod = gmp_mod($x, $mersenne);
        return gmp_mod(gmp_add(gmp_mul($a, $xMod), $b), $mersenne);
    }

    /**
     * Create MinHash signature for a set of tokens.
     *
     * @return \GMP[] Signature array
     */
    public static function minhash(array $tokens, int $numPerm = 128): array
    {
        $mask = gmp_sub(gmp_pow(2, 64), 1);
        $params = self::generateHashParams($numPerm);
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
     * Estimate Jaccard similarity from MinHash signatures.
     */
    public static function jaccardEstimate(array $sigA, array $sigB): float
    {
        if (count($sigA) !== count($sigB)) {
            throw new \InvalidArgumentException('signatures must have same length');
        }
        $matches = 0;
        for ($i = 0; $i < count($sigA); $i++) {
            if (gmp_cmp($sigA[$i], $sigB[$i]) === 0) {
                $matches++;
            }
        }
        return $matches / count($sigA);
    }

    // ============================================================
    // LSH Index
    // ============================================================

    private int $lshBands;
    private int $lshRows;
    private array $lshBuckets;

    public function initLsh(int $bands, int $rows): void
    {
        $this->lshBands = $bands;
        $this->lshRows = $rows;
        $this->lshBuckets = array_fill(0, $bands, []);
    }

    public function lshThreshold(): float
    {
        return pow(1.0 / $this->lshBands, 1.0 / $this->lshRows);
    }

    private function lshBandHash(array $bandValues): string
    {
        $h = gmp_init(self::FNV64_OFFSET);
        $prime = gmp_init(self::FNV64_PRIME);
        $mask = gmp_sub(gmp_pow(2, 64), 1);
        foreach ($bandValues as $val) {
            for ($byteIdx = 0; $byteIdx < 8; $byteIdx++) {
                $byte = gmp_intval(gmp_and(gmp_div_q($val, gmp_pow(2, $byteIdx * 8)), gmp_init(0xFF)));
                $h = gmp_xor($h, gmp_init($byte));
                $h = gmp_and(gmp_mul($h, $prime), $mask);
            }
        }
        return gmp_strval($h);
    }

    public function lshInsert(string $docId, array $signature): void
    {
        for ($b = 0; $b < $this->lshBands; $b++) {
            $start = $b * $this->lshRows;
            $bandVals = array_slice($signature, $start, $this->lshRows);
            $key = $this->lshBandHash($bandVals);
            $this->lshBuckets[$b][$key][] = $docId;
        }
    }

    public function lshQuery(array $signature): array
    {
        $candidates = [];
        for ($b = 0; $b < $this->lshBands; $b++) {
            $start = $b * $this->lshRows;
            $bandVals = array_slice($signature, $start, $this->lshRows);
            $key = $this->lshBandHash($bandVals);
            if (isset($this->lshBuckets[$b][$key])) {
                foreach ($this->lshBuckets[$b][$key] as $doc) {
                    $candidates[$doc] = true;
                }
            }
        }
        $result = array_keys($candidates);
        sort($result);
        return $result;
    }

    public function lshRemove(string $docId, array $signature): void
    {
        for ($b = 0; $b < $this->lshBands; $b++) {
            $start = $b * $this->lshRows;
            $bandVals = array_slice($signature, $start, $this->lshRows);
            $key = $this->lshBandHash($bandVals);
            if (isset($this->lshBuckets[$b][$key])) {
                $this->lshBuckets[$b][$key] = array_values(
                    array_filter($this->lshBuckets[$b][$key], fn($d) => $d !== $docId)
                );
            }
        }
    }
}
