# LombokSimHash (PHP)

Near-duplicate document detection for RAG pipelines — SimHash, MinHash, LSH, SHA-256, and shingling. Uses the GMP extension for 64-bit math.

```bash
composer require codinglombok/lomboksimhash
```

```php
use CodingLombok\LombokSimHash\LombokSimHash;

$a = LombokSimHash::simhash64Text('the quick brown fox jumps over the lazy dog');
$b = LombokSimHash::simhash64Text('the quick brown cat jumps over the lazy dog');
echo LombokSimHash::hamming64($a, $b);  // 8
```

Requires PHP >= 8.1 with `ext-gmp`. Part of [LombokRAGFrameworks](https://github.com/codinglombok/LombokSimHash).

License: Apache-2.0
