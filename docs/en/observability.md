# Observability

**Target Audience**: SREs, Systems Operators
**Objective**: Document integration procedures for centralized logging fabrics (Datadog, Splunk, ELK) and indexable metric generation.
**Scope**: Structured machine instrumentation in `ragprep/core/logging.py` delivering `metrics.json`.

---

## 1. Structured JSON Logging

Linear string logs severely restrict advanced filtering and real-time alerting systems. Integrating the `python-json-logger`, this pipeline normalizes every emitted sequence into strictly typed, machine-readable JSON payloads.

### Default Field Specification

| JSON Key | Type | Logical Description |
| :--- | :--- | :--- |
| `timestamp` | String | ISO-8601 standardized UTC/Local format |
| `level` | Enum | Classification severity (`INFO`, `WARNING`, `ERROR`) |
| `name` | String | Internal Logger Handle (e.g., `ragprep.router`) |
| `run_id` | String | Unique V4 UUID binding a distinct batch iteration |
| `doc_id` | String | Primary identity target of the log event |
| `group_id` | String | Sub-folder collection entity under the merge-group |
| `stage` | String | Code architecture location (`extractor`, `normalizer`) |
| `event` | String | Lifecycle transition hook (`stage_start`, `stage_end`) |
| `duration_ms` | Integer | Epoch delta quantifying the processing bottleneck |
| `message` | String | Concatenated human summary descriptor |

## 2. Metrics Payload Signature

Upon full completion of the terminal task, the pipeline distills universal execution health into a distinct analytical map located inside `data/runs/{run_id}/metrics.json`. This object facilitates immediate regression tests during continuous deployment rollouts.

```json
{
  "run_id": "8b3401fa",
  "total_duration_sec": 34.12,
  "docs_processed": 542,
  "quarantine_rate": 0.05,
  "duration_p95_ms": 120,
  "duration_mean_ms": 45
}
```

## 3. Tactical Troubleshooting Operations

- **Trace a Specific Failure Event**: Query Elasticsearch/Kibana using `doc_id: "xyz123"` to immediately track the exact `stage` the file was scanned, parsed, and abruptly diverted into the Quarantine bucket.
- **Profiling I/O Bottlenecks**: Sort global logs by querying the maximal `duration_ms` payload fields. This rapidly highlights un-indexed SQLite calls or heavy string manipulations suitable for future refactoring efforts.
