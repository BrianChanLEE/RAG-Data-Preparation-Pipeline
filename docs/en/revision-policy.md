# Revision Policy

**Target Audience**: Pipeline Engineers, Version Strategy Managers
**Objective**: Understand the architecture safeguarding text history and rollback capabilities.
**Scope**: Hash differentials and version progression logic in `ragprep/core/structure.py`.

---

## 1. Doc_ID Identifier Concept

The `doc_id` fundamentally unifies the underlying physical filename (like `01.xml`) and its parent folder context (`test_group`), sometimes merging cryptographic hashes. This ensures the output serves as a Single Source of Truth in the RAG architecture. When `--merge-group` triggers, the grouped folder transforms into the absolute marker: `test_group-merged`.

## 2. Trigger Logic for Revision Escalation

The pipeline refuses to blindly overwrite or squander I/O resources on unchanged semantics.

```mermaid
flowchart LR
    A[Normalized Input] --> B[Generate SHA256 Checksum]
    B --> C{Old Document.json<br>Exists?}
    C -- "YES (Exists)" --> D{Hash Match?}
    C -- "NO (New)" --> E[Set Revision = 1]
    
    D -- "Mismatch (Changed)" --> F[Migrate Old File to Revisions/]
    F --> G[Revision = Old + 1]
    D -- "Match (Identical)" --> H[Keep Revision (Overwrite/Skip)]
    
    E --> I((Persist))
    G --> I((Persist))
    H --> I((Persist))
```

The system calculates a `SHA256` checksum matching the aggregated textual corpus. It contrasts this with the `normalized_sha256` existing inside the legacy `document.json`.
- A single byte alteration yields a disparate hash.
- This discrepancy instantly prompts a **Snapshot Backup** before assigning the new text incremented version tags.

## 3. Disaster Rollback and Artifact Migration

During an incremental revision event (Revision + n), the superseded document is meticulously transported out of the live directory.
It physically relocates to the `data/prepared/documents/revisions/{old_revision}/` backup tier.
This mechanism inherently builds an accessible historical tree, offering instantaneous reversion if corrupted data streams infiltrate the infrastructure workflow.
