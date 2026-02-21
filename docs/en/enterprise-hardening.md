# Enterprise Hardening (Operations Guide)

**Target Audience**: DevSecOps, Release Reliability Teams
**Objective**: Serve as the authoritative Checklist and Playbook for configuring system permissions, establishing fault-recovery mechanisms, and understanding the Dead Letter Queue routing schema.

---

## 1. Operations Hardening Checklist

| Domain | Validation Check | Administrator Action Required | Status |
| :--- | :--- | :--- | :---: |
| **Security** | `PII Masking` Toggle Checked | Enforce application-layer regex rules ensuring that `SSNs`, `Phones`, and `Emails` never navigate into Vector Space environments in plaintext. | [ ] |
| **Permissions** | Verify `umask` Systems Var | Prevent default `Other(Everyone)` group permission infiltration. Define bash profile scripts or systemctl instances dictating Linux permissions (e.g., `0640` `r--`). | [ ] |
| **Telemetry** | Observability Agent Tethering | Map Datadog/Splunk Daemon readers targeting `rag-prepare-{run_id}.log` payloads. Configure index filters for the JSON output. | [ ] |
| **Capability** | Verify Target `Executor` Topology | Determine Server RAM and Core availability to definitively elect `--executor process` or `thread` depending strictly upon storage IOPS limitations. | [ ] |

## 2. Dead Letter Queue (DLQ) Methodology

When error conditions exceed exponential back-off thresholds, pipeline processors will not endlessly spin or quietly abandon files in a temporary state. Instead, they seamlessly isolate failed sources natively inside the debug-friendly `data/dlq/{doc_id}/` storage tier.

```mermaid
flowchart TD
    Error{Exception Occurs} --> Retry[Retry Exponential Backoff]
    Retry --> Error
    Error -- "Max Retries Breached" --> Move[Mirror Document File]
    Move --> DLQ>data/dlq/{doc_id}/original.pdf]
    Move --> Log>data/dlq/{doc_id}/error.log]
```

**[Incident Response Protocol]**
1. Automated Observability alerts index the failure logs bridging Datadog queues.
2. The operational responder introspects the specified `data/dlq/{doc_id}/error.log` reading Python-generated Unhandled Exceptions (`UNHANDLED_ERROR`).
3. Engineers deduce corrupted bitstreams or broken formatting constraints within the `dlq/` source inputs. Pydantic parser patches are crafted to accommodate extreme deviations.

## 3. Reprocessing Repositories

Following successful bug hotfixes or manual mitigation resolution, stagnant payloads mandate re-indexing.

- **Pipeline Overwriting Iterations**: By virtue of 100% IDEMPOTENCY, administrators may fearlessly re-launch full pipeline cycles against `data/raw/` stores. Existing documents will rapidly bypass all phases due to verification flags (`#success.json`), directing processing resources distinctly to untagged DLQ documents returning to the primary staging folder.
- **Cache Eviction**: Utilizing the terminal flag `--force` enforces absolute environment reprocessing. All Hash-comparisons ignore bypassing and forcefully construct new historical Snapshots (`revisions`) validating ultimate RAG fidelity.
