<?php

/**
 * LombokSimHash — LSH index (band+row) over MinHash signatures.
 *
 * Part of LombokRAGFrameworks (Lombok Ecosystem).
 * Behavior is pinned by docs/SPEC_LombokSimHash_0.1.0.md and the shared
 * cross-language vectors (vectors/lomboksimhash-vectors-v2.json).
 *
 * @license Apache-2.0
 */

namespace CodingLombok\LombokSimHash;

final class LshIndex
{
    private const FNV64_OFFSET = '14695981039346656037'; // 0xcbf29ce484222325
    private const FNV64_PRIME  = '1099511628211';        // 0x100000001b3
    private const MASK64       = '18446744073709551615'; // 2^64 - 1

    private int $bands;
    private int $rows;

    /** @var array<int, array<string, list<string>>> */
    private array $buckets;

    public function __construct(int $bands, int $rows)
    {
        if ($bands < 1 || $rows < 1) {
            throw new \InvalidArgumentException(
                '[ERR_LSH_CONFIG] bands and rows must be > 0'
            );
        }
        $this->bands = $bands;
        $this->rows = $rows;
        $this->buckets = array_fill(0, $bands, []);
    }

    public function bands(): int
    {
        return $this->bands;
    }

    public function rows(): int
    {
        return $this->rows;
    }

    public function signatureLen(): int
    {
        return $this->bands * $this->rows;
    }

    /**
     * Approximate Jaccard threshold (1/bands)^(1/rows).
     * Informational only — not part of the bit-identical contract.
     */
    public function threshold(): float
    {
        return pow(1.0 / $this->bands, 1.0 / $this->rows);
    }

    /**
     * Insert a document's MinHash signature into the index.
     *
     * @param list<\GMP> $signature
     */
    public function insert(string $docId, array $signature): void
    {
        $this->assertSignatureLen($signature);
        for ($b = 0; $b < $this->bands; $b++) {
            $start = $b * $this->rows;
            $bandVals = array_slice($signature, $start, $this->rows);
            $key = $this->bandHash($bandVals);
            $this->buckets[$b][$key][] = $docId;
        }
    }

    /**
     * Query candidate near-duplicates. Returns sorted, de-duplicated doc IDs.
     *
     * @param list<\GMP> $signature
     * @return list<string>
     */
    public function query(array $signature): array
    {
        $this->assertSignatureLen($signature);
        $candidates = [];
        for ($b = 0; $b < $this->bands; $b++) {
            $start = $b * $this->rows;
            $bandVals = array_slice($signature, $start, $this->rows);
            $key = $this->bandHash($bandVals);
            foreach ($this->buckets[$b][$key] ?? [] as $doc) {
                $candidates[$doc] = true;
            }
        }
        $result = array_keys($candidates);
        sort($result, SORT_STRING);
        return $result;
    }

    /**
     * Remove all occurrences of a doc ID touched by this signature.
     *
     * @param list<\GMP> $signature
     */
    public function remove(string $docId, array $signature): void
    {
        $this->assertSignatureLen($signature);
        for ($b = 0; $b < $this->bands; $b++) {
            $start = $b * $this->rows;
            $bandVals = array_slice($signature, $start, $this->rows);
            $key = $this->bandHash($bandVals);
            if (isset($this->buckets[$b][$key])) {
                $this->buckets[$b][$key] = array_values(array_filter(
                    $this->buckets[$b][$key],
                    static fn (string $d): bool => $d !== $docId
                ));
            }
        }
    }

    /**
     * @param list<\GMP> $signature
     */
    private function assertSignatureLen(array $signature): void
    {
        if (count($signature) !== $this->signatureLen()) {
            throw new \InvalidArgumentException(sprintf(
                '[ERR_SIG_LEN] signature length must be bands * rows = %d',
                $this->signatureLen()
            ));
        }
    }

    /**
     * FNV-1a 64 over the little-endian bytes of each band value.
     *
     * @param list<\GMP> $bandValues
     */
    private function bandHash(array $bandValues): string
    {
        $h = gmp_init(self::FNV64_OFFSET);
        $prime = gmp_init(self::FNV64_PRIME);
        $mask = gmp_init(self::MASK64);
        $ff = gmp_init(0xFF);
        foreach ($bandValues as $val) {
            $v = $val;
            for ($byteIdx = 0; $byteIdx < 8; $byteIdx++) {
                // exponent <= 56 < 64: gmp_pow is safe on every PHP build
                // (gmp_pow throws for exponent >= 64 on some builds).
                $shifted = gmp_div_q($v, gmp_pow(2, $byteIdx * 8));
                $byte = gmp_intval(gmp_and($shifted, $ff));
                $h = gmp_xor($h, gmp_init($byte));
                $h = gmp_and(gmp_mul($h, $prime), $mask);
            }
        }
        return gmp_strval($h);
    }
}
