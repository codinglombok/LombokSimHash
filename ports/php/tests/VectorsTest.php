<?php

declare(strict_types=1);

namespace CodingLombok\LombokSimHash\Tests;

use CodingLombok\LombokSimHash\LshIndex;
use CodingLombok\LombokSimHash\LombokSimHash;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

/**
 * Vector tests: consume the ONE shared cross-language vectors file
 * (vectors/lomboksimhash-vectors-v2.json) — same file as Rust/TS/Python/Go.
 * Comparisons are exact hex, never near-equality.
 */
final class VectorsTest extends TestCase
{
    private const VECTOR_FILE = __DIR__ . '/../../../vectors/lomboksimhash-vectors-v2.json';

    /** @var array{schema: string, cases: array<string, list<array<string, mixed>>>}|null */
    private static ?array $doc = null;

    /** @return array{schema: string, cases: array<string, list<array<string, mixed>>>} */
    private static function doc(): array
    {
        if (self::$doc === null) {
            $raw = file_get_contents(self::VECTOR_FILE);
            self::assertNotFalse($raw, 'vectors readable at ' . self::VECTOR_FILE);
            $parsed = json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
            self::assertIsArray($parsed);
            self::assertIsString($parsed['schema'] ?? null);
            self::assertSame('lomboksimhash-vectors-v2', $parsed['schema']);
            self::assertIsArray($parsed['cases'] ?? null);
            foreach ($parsed['cases'] as $section) {
                self::assertIsArray($section);
            }
            /** @var array{schema: string, cases: array<string, list<array<string, mixed>>>} $parsed */
            self::$doc = $parsed;
        }
        return self::$doc;
    }

    /** @return iterable<string, array{string, array<string, mixed>}> */
    public static function provideSha256(): iterable
    {
        foreach (self::doc()['cases']['sha256'] as $case) {
            yield self::str($case, 'id') => [self::str($case, 'id'), $case];
        }
    }

    #[DataProvider('provideSha256')]
    public function testSha256(string $id, array $case): void
    {
        $data = isset($case['input'])
            ? self::str($case, 'input')
            : self::bytesHex(self::str($case, 'input_hex'));
        self::assertSame(self::str($case, 'expected_hex'), LombokSimHash::sha256($data), "case $id");
    }

    /** @return iterable<string, array{string, array<string, mixed>}> */
    public static function provideFnv(): iterable
    {
        foreach (self::doc()['cases']['fnv1a64'] as $case) {
            yield self::str($case, 'id') => [self::str($case, 'id'), $case];
        }
    }

    #[DataProvider('provideFnv')]
    public function testFnv1a64(string $id, array $case): void
    {
        $data = self::bytesHex(self::str($case, 'input_hex'));
        $got = self::pad64(gmp_strval(LombokSimHash::fnv1a64($data), 16));
        self::assertSame(self::str($case, 'expected_hex'), $got, "case $id");
    }

    /** @return iterable<string, array{string, array<string, mixed>}> */
    public static function provideShingle(): iterable
    {
        foreach (self::doc()['cases']['shingle'] as $case) {
            yield self::str($case, 'id') => [self::str($case, 'id'), $case];
        }
    }

    #[DataProvider('provideShingle')]
    public function testShingle(string $id, array $case): void
    {
        $mode = self::str($case, 'mode');
        $got = $mode === 'character'
            ? LombokSimHash::charShingles(self::str($case, 'input'), self::intVal($case, 'n'))
            : LombokSimHash::wordShingles(self::str($case, 'input'), self::intVal($case, 'n'));
        self::assertSame(self::strList($case, 'expected'), $got, "case $id");
    }

    /** @return iterable<string, array{string, array<string, mixed>}> */
    public static function provideSimhash64(): iterable
    {
        foreach (self::doc()['cases']['simhash64'] as $case) {
            yield self::str($case, 'id') => [self::str($case, 'id'), $case];
        }
    }

    #[DataProvider('provideSimhash64')]
    public function testSimhash64(string $id, array $case): void
    {
        $hash = LombokSimHash::simhash64Text(self::str($case, 'input'));
        self::assertSame(self::str($case, 'expected_hex'), self::pad64(gmp_strval($hash, 16)), "case $id");
    }

    /** @return iterable<string, array{string, array<string, mixed>}> */
    public static function provideSimhash128(): iterable
    {
        foreach (self::doc()['cases']['simhash128'] as $case) {
            yield self::str($case, 'id') => [self::str($case, 'id'), $case];
        }
    }

    #[DataProvider('provideSimhash128')]
    public function testSimhash128(string $id, array $case): void
    {
        [$hi, $lo] = LombokSimHash::simhash128Text(self::str($case, 'input'));
        $hiHex = self::pad64(gmp_strval($hi, 16));
        $loHex = self::pad64(gmp_strval($lo, 16));
        self::assertSame(self::str($case, 'hi_hex'), $hiHex, "case $id hi");
        self::assertSame(self::str($case, 'lo_hex'), $loHex, "case $id lo");
        self::assertSame(self::str($case, 'hex'), $hiHex . $loHex, "case $id hex");
    }

    /** @return iterable<string, array{string, array<string, mixed>}> */
    public static function provideMinhashSignature(): iterable
    {
        foreach (self::doc()['cases']['minhash_signature'] as $case) {
            yield self::str($case, 'id') => [self::str($case, 'id'), $case];
        }
    }

    #[DataProvider('provideMinhashSignature')]
    public function testMinhashSignature(string $id, array $case): void
    {
        $sig = LombokSimHash::minhash(self::strList($case, 'tokens'), self::intVal($case, 'num_perm'));
        $got = array_map(
            static fn (\GMP $v): string => self::pad64(gmp_strval($v, 16)),
            $sig
        );
        self::assertSame(self::strList($case, 'signature_hex'), $got, "case $id");
    }

    /** @return iterable<string, array{string, array<string, mixed>}> */
    public static function provideMinhashJaccard(): iterable
    {
        foreach (self::doc()['cases']['minhash_jaccard'] as $case) {
            yield self::str($case, 'id') => [self::str($case, 'id'), $case];
        }
    }

    #[DataProvider('provideMinhashJaccard')]
    public function testMinhashJaccard(string $id, array $case): void
    {
        $numPerm = self::intVal($case, 'num_perm');
        $a = LombokSimHash::minhash(self::strList($case, 'set_a'), $numPerm);
        $b = LombokSimHash::minhash(self::strList($case, 'set_b'), $numPerm);
        $matches = 0;
        for ($i = 0; $i < $numPerm; $i++) {
            if (gmp_cmp($a[$i], $b[$i]) === 0) {
                $matches++;
            }
        }
        self::assertSame(self::intVal($case, 'expected_matches'), $matches, "case $id");
    }

    /** @return iterable<string, array{string, array<string, mixed>}> */
    public static function provideLshIndex(): iterable
    {
        foreach (self::doc()['cases']['lsh_index'] as $case) {
            yield self::str($case, 'id') => [self::str($case, 'id'), $case];
        }
    }

    #[DataProvider('provideLshIndex')]
    public function testLshIndex(string $id, array $case): void
    {
        $idx = new LshIndex(self::intVal($case, 'bands'), self::intVal($case, 'rows'));
        foreach (self::rows($case, 'inserts') as $ins) {
            $idx->insert(self::str($ins, 'doc_id'), self::sigFromHex(self::strList($ins, 'signature_hex')));
        }
        $got = $idx->query(self::sigFromHex(self::strList($case, 'query_hex')));
        self::assertSame(self::strList($case, 'expected'), $got, "case $id");

        if (isset($case['remove']) && is_array($case['remove'])) {
            $remove = $case['remove'];
            $idx->remove(self::str($remove, 'doc_id'), self::sigFromHex(self::strList($remove, 'signature_hex')));
            $after = $idx->query(self::sigFromHex(self::strList($case, 'query_hex')));
            self::assertSame(self::strList($case, 'expected_after_remove'), $after, "case $id after remove");
        }
    }

    // ---- typed accessors for json-decoded vectors ----

    /** @param array<string, mixed> $case */
    private static function str(array $case, string $key): string
    {
        $v = $case[$key] ?? null;
        self::assertIsString($v, "expected string for '$key'");
        return $v;
    }

    /** @param array<string, mixed> $case */
    private static function intVal(array $case, string $key): int
    {
        $v = $case[$key] ?? null;
        self::assertIsInt($v, "expected int for '$key'");
        return $v;
    }

    /** @return list<string> */
    private static function strList(array $case, string $key): array
    {
        $v = $case[$key] ?? null;
        self::assertIsList($v, "expected list for '$key'");
        return array_map(
            static function ($item): string {
                self::assertIsString($item);
                return $item;
            },
            $v
        );
    }

    /**
     * @param array<string, mixed> $case
     * @return list<array<string, mixed>>
     */
    private static function rows(array $case, string $key): array
    {
        $v = $case[$key] ?? null;
        self::assertIsList($v, "expected list for '$key'");
        return array_map(
            static function ($item): array {
                self::assertIsArray($item);
                return $item;
            },
            $v
        );
    }

    /** @param list<string> $hexes @return list<\GMP> */
    private static function sigFromHex(array $hexes): array
    {
        return array_map(static fn (string $h): \GMP => gmp_init($h, 16), $hexes);
    }

    private static function pad64(string $hex): string
    {
        return str_pad($hex, 16, '0', STR_PAD_LEFT);
    }

    private static function bytesHex(string $hex): string
    {
        $bytes = hex2bin($hex);
        self::assertNotFalse($bytes);
        return $bytes;
    }
}
