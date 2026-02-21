# Failure Handling

**Target Audience**: L2/L3 Application Support, Incident Managers
**Objective**: Map mechanisms responsible for preserving application integrity amidst unrecoverable syntax abnormalities.

---

## 1. Trilateral Defensive Lines

On-premises enterprise architectures handling massive payloads strictly prohibit singular defective nodes from crashing collective iterations. A 3-tier cascade of operational safeguards intercepts cascading failures.

1. **Partial Success Recovery**: Encountering corrupted singular elements inside multi-layered ZIP (JWPUBs) bypasses typical process halts. Systems return `True` flags attaching internal metrics via `extract_warnings`, ensuring healthy remaining segments persist.
2. **Exponential Backoff Threading**: Recognizing ephemeral filesystem latency bottlenecks, `Executor` components natively invoke sleep intervals expanding exponentially pre-reattempt.
3. **Escalation (DLQ/Quarantine)**: Files irreparably crippled across exhaustive threads gracefully bypass primary memory arrays logging specific stack traces inside the `dlq/` vault.

## 2. Exception Incident Playbook

| Runtime Signature | Trigger Hypothesis | Administrator Resolution Action |
| :--- | :--- | :--- |
| `Zip bomb detected: {size} > {MAX}` | Extremely large or intentionally malicious cyclic archives. | Eject and physically eradicate the underlying structure situated inside `quarantine/`. |
| `UNHANDLED_ERROR` in `router.py` | Encoding fractures or deeply unexpected structural destructions breaking parser models. | Trace manual executions explicitly tracking payloads dropped inside the `data/dlq/` sandbox. |
| `QualityDecision.REVIEW` & `Too many short chunks` | Overrepresentation of isolated fragments common across specialized thematic inputs (Bible Verses). | Verify the analytical accuracy manually triggering backend uploads directly out of the `review/` compartment. |

## 3. Queue Resolution Framework

Post structural debugging, documents must efficiently re-inject toward staging areas.

Moving assets from `data/dlq` backwards into `data/raw/` enables automated reprocessing vectors via pipeline idelmpotency mechanisms. The `#success.json` mechanism recognizes existing achievements across 99% of identical databases instantaneously hopping specifically onto the singular isolated anomaly.

```bash
python -m ragprep.prepare --executor thread
```
