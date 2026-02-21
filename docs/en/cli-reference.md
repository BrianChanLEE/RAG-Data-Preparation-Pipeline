# CLI Reference

**Target Audience**: Operations, MLOps Integration Teams
**Objective**: Summarize the primary terminal invocation parameters governing pipeline manipulation architectures.
**Scope**: Configuration commands natively defined in `ragprep/prepare.py`.

---

## 1. Execution Arguments Manifest

Leveraging `argparse`, system integrators possess deep capabilities adjusting multi-threading boundaries, memory constraints, and logical clustering tactics without ever editing underlying codebase definitions. 

| Argument (`Flag`) | Data Class / Default | Behavioral Concept | Tactic Profile |
| :--- | :--- | :--- | :--- |
| `--input-dir` | Path (`data/raw`) | Anchor directory where raw (`.pdf`, `.xml`, `.jwpub`) inputs reside. Recursive traversal engaged. | Standard Mount |
| `--output-dir` | Path (`data/prepared`) | Unified workspace capturing normalizations, chunks, success flags, and metrics reports. | Standard Mount |
| `--force` | Boolean Toggle | Triggers massive scale override algorithms aggressively bypassing `#success.json` skips; forcing total recalculations. | Total DB Resets |
| `--concurrency` | Integer (`CPU/2`) | Artificial boundaries suppressing internal Python Pool deployments throttling simultaneous parsing streams. | I/O Expansion |
| `--merge-group` | String (`false`) | Enables complex concatenation logics unifying thousands of scattered XML instances into monolithic thematic Group Contexts. | Biblical Data |
| `--min-chars` | Integer (`300`) | Length thresholds identifying malformed documents lacking sufficient structural string lengths for LLM usage. | Quality Defense |
| `--quality-gate` | String (`true`) | Instructs pipeline architectures to filter outputs against heuristics routing artifacts inside `quarantine/` structures. | Mandatory |
| `--dedupe` | String (`true`) | Prevents similar phrases or overlapping content blocks from flooding Top-K results. In-memory comparisons active. | Strict Isolation |
| `--dedupe-scope`| String (`doc`\|`group`) | Dictates if Deduplication footprint histories persist natively intra-document (`doc`) or holistically cross-folders (`group`). | Advanced Filter |
| `--pii-mask` | Boolean Toggle | Protects privacy substituting regex patterns identifying cell numbers, IDs, and email arrays. | SecOps Requirement |
| `--executor` | String (`process`\|`thread`) | Swaps multi-core architecture frameworks mitigating global interpreter lock delays against single-thread overheads. | `process` preferred |
| `--max-retries` | Integer (`1`) | Governs sequential attempts combating intermittent parsing crashes utilizing exponent backoffs. | 2~3 |
| `--retry-backoff-ms` | Integer (`2000`) | Initial latency duration measured milliseconds (ms) awaiting subsequent file execution. Scale doubles upon cascading failures. | Throttling |

## 2. Command Line Playbooks

**✅ Debug Sandbox Isolation (Minimal Concurrency)**  
(Optimally suited for low-memory micro-instances analyzing stack traces)
```bash
python -m ragprep.prepare --force --concurrency 1 --executor thread --pii-mask
```

**✅ Global Bible/Journal Data Assimilation Strategy**  
(Massive document pools needing context grouping and severe group-level Deduplication filters)
```bash
python -m ragprep.prepare --merge-group true --dedupe-scope group
```
