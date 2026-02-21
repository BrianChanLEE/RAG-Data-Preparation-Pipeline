# FAQ

**Target Audience**: Developers, End Users
**Objective**: Rapidly remedy common implementation obstacles circumventing unnecessary operational escalations.

---

## Q1. The pipeline executed successfully but nothing generated declaring `Found 0 files`?
**A**: Re-validate the target `--input-dir`. Absolute default paths navigate strictly against `/data/raw`. All files mandate correct syntax extensions `.pdf`, `.xml`, `.jwpub`. The scanner universally ignores hidden metadata instances or ambiguous extensions.

## Q2. Modifying singular documents never triggers `revisions/` snapshot updates?
**A**: Idempotent mechanisms dictate system conservation policies. Emitting `#success.json` signals permanent task closures evading duplicate processing costs natively.
- **Remedy**: Re-executing altered documentation demands passing the `--force` toggle. Overriding caches subsequently compares internal hashes (SHA256) archiving new versions generating exact snapshot diffs.

## Q3. Are outputs structurally identical contrasting `--executor process` versus `thread`?
**A**: Yes. Resulting analytical fidelity represents absolute `100%` identical precision. Swapping architectures exclusively mitigates global lock CPU processing against local I/O overheads. Select `thread` for light high-volume batches and `process` targeting massive heavy files.

## Q4. May I manipulate external Quality Gates or NLP overlaps overriding the command arguments?
**A**: Artificial bounds actively protect Vector Database consistency. Consequently, manipulating `QualityDecision` tolerances demands explicit code-level configurations explicitly walled off from simplistic CLI overrides. Inspect the primary `configuration-guide.md` targeting core infrastructure manipulation.

## Q5. Resulting Output folders indicate a reduction losing specific file clusters?
**A**: Structural defects or inadequate text length constraints block payloads cascading further down integration sequences triggering Human-in-the-Loop interventions. 
- Inspect the physical boundaries attached inside `data/review/` or `data/quarantine/` detecting dropped content.
- Opening accompanying `quality.json` files displays concise `reasons` highlighting directly what structural threshold prohibited total ingestion.
