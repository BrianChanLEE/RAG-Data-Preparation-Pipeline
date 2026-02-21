# Deduplication Strategy

**Target Audience**: Search Relevance Engineers
**Objective**: Mitigate redundant chunk propagation that spoils similarity matching within the Vector Database.
**Scope**: Offline Jaccard similarity and N-gram mechanisms within `ragprep/core/dedupe.py`.

---

## 1. Context Pollution & Near-Duplicates

Prolonged redundant paragraphs (like repetitive prefaces or legal disclaimers) present a catastrophic risk during RAG Top-K Vector Retrieval. If identical texts flood the Vector Space, genuine informative contexts are crowded out, a phenomenon coined "Context Pollution."
Hence, relying on Exact Match schemas is futile. The system must autonomously detect Near-Duplicate variations—sentences sharing an overwhelming vocabulary signature.

## 2. In-Memory N-gram Fingerprinting

This module deploys a dependency-less, Python-native fingerprint tracker avoiding heavy external graphs like SimHash.

```mermaid
graph TD
    A[Raw Text Chunk] -->|Lowercase| B[Word Tokenization]
    B -->|N=3 grouping| C[N-gram Set Creation]
    C --> D[Historical Fingerprint DB (RAM)]
    D --> E{Jaccard Metric}
    
    E -- "Similarity >= 0.85" --> F(Duplicate - SKIP)
    E -- "Similarity < 0.85" --> G(Unique - SAVE)
    G --> H[Register into DB]
```

- **Jaccard Similarity**: Evaluates `Intersection / Union` ratios of lexical N-grams. Chunks surpassing the default `0.85` threshold (meaning 85% equivalence) are statistically deemed structural duplicates.
- All empty strings or abnormally short blocks are algorithmically bypassed to minimize memory overhead.

## 3. Deduplication Scope Hierarchy

Executing `--dedupe-scope` shapes the "Memory Limit" of the filter to balance analytical precision against computational costs.

| Syntax Flag | Mechanistic Explanation | Advantages |
| :--- | :--- | :--- |
| `doc` | **Intra-Document Isolation**: The fingerprint dictionary completely flushes between distinct files (`doc_id`). It exclusively hunts for inner repetitions (like page footers or persistent titles). | Maximum speed and minimal RAM overhead. Prevents severe false-positive accidents. (Default) |
| `group` | **Inter-Group Aggregation**: Synchronizes deductive memory across multiple files nested under a shared `--merge-group` path. | Extremely robust for dissecting thousands of fragmented biblical XMLs or sequential HR Manual policies where repetition spans across physical OS boundaries. |
