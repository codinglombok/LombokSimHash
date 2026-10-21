<?php

declare(strict_types=1);

namespace CodingLombok\LombokSimHash\Tests;

use CodingLombok\LombokSimHash\LombokSimHash;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

/**
 * Error contract + edge cases for the PHP port.
 */
final class LombokSimHashTest extends TestCase
{
    public static function provideErrorContract(): array
    {
        return [
            ['shingle n zero', '[ERR_SHINGLE_N] shingle size must be > 0', static fn () => LombokSimHash::charShingles('abc', 0)],
            ['shingle n negative', '[ERR_SHINGLE_N] shingle size must be > 0', static fn () => LombokSimHash::wordShingles('a b', -1)],
            ['minhash zero perm', '[ERR_MINHASH_PERM] num_perm must be > 0', static fn () => LombokSimHash::minhash(['a'], 0)],
            ['jaccard len mismatch', '[ERR_JACCARD_LEN] signatures must have same length', static function (): void {
                $a = LombokSimHash::minhash(['a'], 8);
                $b = LombokSimHash::minhash(['b'], 16);
                LombokSimHash::jaccardEstimate($a, $b);
            }],
            ['jaccard empty', '[ERR_JACCARD_EMPTY] signatures must not be empty', static fn () => LombokSimHash::jaccardEstimate([], [])],
        ];
    }

    #[DataProvider('provideErrorContract')]
    public function testErrorContract(string $label, string $expected, callable $action): void
    {
        $this->expectException(\InvalidArgumentException::class);
        $this->expectExceptionMessage($expected);
        $action();
    }

    public function testSha256Reference(): void
    {
        self::assertSame(
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
            LombokSimHash::sha256('')
        );
        self::assertSame(
            'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
            LombokSimHash::sha256('abc')
        );
    }

    public function testFnvOffsetAndKnown(): void
    {
        self::assertSame('cbf29ce484222325', gmp_strval(LombokSimHash::fnv1a64(''), 16));
        self::assertSame('a430d84680aabd0b', gmp_strval(LombokSimHash::fnv1a64('hello'), 16));
    }

    public function testTokenizeSpecSet(): void
    {
        $tokens = LombokSimHash::tokenize("a\u{00A0}b\u{3000}c\u{000B}d");
        self::assertSame(['a', 'b', 'c', 'd'], $tokens);
        // ZWSP / BOM are NOT in the SPEC whitespace set
        self::assertSame(["a\u{200B}b"], LombokSimHash::tokenize("a\u{200B}b"));
        self::assertSame([], LombokSimHash::tokenize(" \t\n\u{00A0}"));
    }

    public function testSimhashKnownValues(): void
    {
        $fox = LombokSimHash::simhash64Text('the quick brown fox jumps over the lazy dog');
        $cat = LombokSimHash::simhash64Text('the quick brown cat jumps over the lazy dog');
        self::assertSame('cab7991c5475edee', self::hex64($fox));
        self::assertSame('c2e7991c1465e56f', self::hex64($cat));
        self::assertSame(8, LombokSimHash::hamming64($fox, $cat));
        self::assertSame('0000000000000000', self::hex64(LombokSimHash::simhash64Text("  \t\n")));
    }

    public function testSimhash128LoMatches64(): void
    {
        $fox = 'the quick brown fox jumps over the lazy dog';
        [$hi, $lo] = LombokSimHash::simhash128Text($fox);
        self::assertSame(self::hex64(LombokSimHash::simhash64Text($fox)), self::hex64($lo));
        self::assertSame(0, LombokSimHash::hamming128([$hi, $lo], [$hi, $lo]));
        self::assertSame(
            self::hex64($hi) . self::hex64($lo),
            self::hex64($hi) . self::hex64($lo)
        );
    }

    public function testShingleEdgeCases(): void
    {
        self::assertSame(['abc', 'bcd', 'cde'], LombokSimHash::charShingles('abcde', 3));
        self::assertSame([], LombokSimHash::charShingles('ab', 5));
        self::assertSame([], LombokSimHash::wordShingles('a b', 4));
        self::assertSame(
            ['hé', 'll', 'lo', 'él'],
            LombokSimHash::charShingles('héllo', 2),
            'code-point slicing + code-point sort'
        );
    }

    public function testMinhashDeterministicAndIdempotent(): void
    {
        $a = LombokSimHash::minhash(['hello', 'world'], 64);
        $b = LombokSimHash::minhash(['world', 'hello', 'hello'], 64);
        self::assertSame(
            array_map(static fn (\GMP $v): string => gmp_strval($v, 16), $a),
            array_map(static fn (\GMP $v): string => gmp_strval($v, 16), $b)
        );
        self::assertSame(64, count($a));
    }

    private static function hex64(\GMP $v): string
    {
        return str_pad(gmp_strval($v, 16), 16, '0', STR_PAD_LEFT);
    }
}
