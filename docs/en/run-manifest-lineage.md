# Run Manifest & Lineage

**Target Audience**: Data Scientists, Compliance Auditors
**Objective**: Elucidate the architectural methodology utilized to trace parameters, AI data boundaries, and exact version snapshots of origin texts long after processing finishes.
**Scope**: `chunk.jsonl` Lineage payload and `ragprep/prepare.py` generated manifests.

---

## 1. Run Manifest Structure (Context Profiling)

RAG engines constantly mutate regarding dependencies and strategies. When diagnosing index discrepancies a year from today, operators must discern exactly what configurations were responsible. Upon graceful termination (or DLQ exits) of a batch cycle, the system automatically emits a JSON profile: `data/runs/{run_id}/manifest.json`.

| Section | Target Fields | Operational Explanation |
| :--- | :--- | :--- |
| **Operational Context** | `run_id`, `started_at`, `finished_at` | Global ID binding the pipeline logs and duration metadata. |
| **Runtime Environment** | `git_commit`, `requirements_hash`, `host_info` | Sever fingerprints, dependency integrity checks, and precise repository states. |
| **Tuning Parameters** | `concurrency`, `pii_mask`, `executor_type` | Absolute record of all configuration variables injected via CLI flags during command initiation. |

## 2. Chunk Lineage Identity Tracking

How does one empirically prove the validity of a solitary extracted sentence navigating through millions of Vector Database fragments? Inside every core text foundation (a Chunk), a dedicated `lineage` meta-object is permanently fused into the serialized database payload.

```json
{
  "chunk_id": "abx-cd-12-c2",
  "text": "In the beginning God created the heaven and the earth...",
  "lineage": {
    "doc_id": "genesis-1-merged",
    "group_id": "genesis",
    "revision": 3,
    "source_paths": [
      "/absolute/path/to/origin/genesis_1.xml"
    ],
    "stage_versions": {
      "schema": "1.0",
      "chunker": "1.0.0"
    }
  }
}
```

This nested `lineage` block solidifies backwards traceability:
- `source_paths`: Unambiguous path revealing the specific origin payload files merged or extracted.
- `revision`: Tangible proof signifying this sentence belonged to the 3rd hash-diffed iteration of the document, validating the recency compared to stale index clusters.
- `stage_versions`: Guarantees the architectural boundaries used to parse the chunks (Version 1.0 Chunker instead of a deprecated legacy module). This facilitates targeted vector re-migrations when critical parser bugs are identified down the line.
