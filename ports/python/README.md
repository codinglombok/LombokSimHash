# LombokSimHash (Python)

Near-duplicate document detection for RAG pipelines — SimHash, MinHash, LSH, SHA-256, and shingling. Pure Python, zero dependencies.

```bash
pip install lomboksimhash
```

```python
from lomboksimhash import simhash64_text, hamming64, MinHasher, jaccard_estimate, LshIndex

a = simhash64_text("the quick brown fox jumps over the lazy dog")
b = simhash64_text("the quick brown cat jumps over the lazy dog")
print(hamming64(a, b))  # 8
```

Part of [LombokRAGFrameworks](https://github.com/codinglombok/LombokSimHash). Full docs in the [main repository](https://github.com/codinglombok/LombokSimHash).

License: Apache-2.0
