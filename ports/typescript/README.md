# LombokSimHash (TypeScript)

Near-duplicate document detection for RAG pipelines — SimHash, MinHash, LSH, SHA-256, and shingling. Pure TypeScript with BigInt, zero dependencies.

```bash
npm install lomboksimhash
```

```typescript
import { simhash64Text, hamming64, MinHasher, jaccardEstimate, LshIndex } from 'lomboksimhash';

const a = simhash64Text('the quick brown fox jumps over the lazy dog');
const b = simhash64Text('the quick brown cat jumps over the lazy dog');
console.log(hamming64(a, b));  // 8
```

Part of [LombokRAGFrameworks](https://github.com/codinglombok/LombokSimHash). Full docs in the [main repository](https://github.com/codinglombok/LombokSimHash).

License: Apache-2.0
