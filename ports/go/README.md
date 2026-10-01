# LombokSimHash (Go)

Near-duplicate document detection for RAG pipelines — SimHash, MinHash, LSH, SHA-256, and shingling. Zero dependencies, uses `math/bits`.

```bash
go get github.com/codinglombok/LombokSimHash
```

```go
import "github.com/codinglombok/LombokSimHash"

a := lomboksimhash.SimHash64Text("the quick brown fox jumps over the lazy dog")
b := lomboksimhash.SimHash64Text("the quick brown cat jumps over the lazy dog")
dist := lomboksimhash.Hamming64(a, b)  // 8
```

Part of [LombokRAGFrameworks](https://github.com/codinglombok/LombokSimHash). Full docs in the [main repository](https://github.com/codinglombok/LombokSimHash).

License: Apache-2.0
