# Pipeline Flow

**Target Audience**: Pipeline Operators, Batch Managers
**Objective**: Visualize the physical and logical path of data from its origin to the RAG DB entry queue.
**Scope**: End-to-end processing from Raw data ingestion to Quality Gate and Dedupe.

---

## Pipeline Lifecycle Diagram

As the pipeline is idempotent, it features 5 persistent checkpoint step-boxes, enabling safe resumption upon unexpected hardware failures.

```mermaid
sequenceDiagram
    participant R as Raw Storage
    participant S as Scanner/Router
    participant E as Extraction/Normalize
    participant C as Chunker
    participant Q as Quality Gate/Dedupe
    participant D as Output/DLQ
    
    R->>S: 1. Scan files
    S->>S: 2. Resolve Group Merge commands
    S->>E: 3. Dispatch FileMeta to Extractor
    activate E
    E->>E: 4. Format Conversion (.pdf/.xml/.jwpub)
    E->>E: 5. Apply PII Masking
    E-->>S: 6. Return Normalized JSON
    deactivate E
    
    S->>C: 7. Dispatch Structurizer
    activate C
    C->>C: 8. Semantic Text Chunking (Generator)
    C-->>S: 9. JSONL Chunk complete
    deactivate C
    
    S->>Q: 10. Eval Quality Metrics (Pass/Review/Fail)
    activate Q
    Q->>Q: 11. Deduplication (Jaccard Hash Analytics)
    Q-->>S: 12. Return routing decision
    deactivate Q
    
    S->>D: 13. Dump to proper Queue (Prepared/DLQ/Quarantine)
```

### Lifecycle Characteristics
- **Step 1~3**: Dispatch FileMeta streams into Thread/Process Pools via the `Executor` to eliminate CPU idle time.
- **Step 4~6**: On-premises disk I/O flushes prevent Out-Of-Memory (OOM) exceptions.
- **Step 7~9**: Utilizes Python Generators (`yield`) during chunking to write to physical drives continuously.
- **Step 10~13**: Prompt folder routing judgments (`mv`/`cp`) are governed by length heuristics and N-gram fingerprints.
