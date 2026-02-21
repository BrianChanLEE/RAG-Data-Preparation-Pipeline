# Configuration Guide

**Target Audience**: Application Administrators
**Objective**: Instruct users on how to recalibrate deeper system invariants encapsulated beyond simple runtime CLI parameters.
**Scope**: Codebase thresholds targeting Zip Defenses, Quality Parameters, and Chunk Sizing.

---

## 1. Deep Core Constants Customizations

Enterprise stability frequently relies upon unexposed defensive heuristics. Scaling RAG solutions demands modifying architectural scripts located directly inside module infrastructures rather than simple command inputs. 

### 🛡 Zip Bomb Parameter Defenses
- **Target File**: `ragprep/core/extract_jwpub.py`
- Enforces strict I/O policies protecting Linux kernels from crashing when unwrapping malevolent ZIP architectures (JWPUBs). Modification necessary exclusively when confronted by highly trusted but enormously large legacy text dumps.
  - `MAX_FILES = 5000` (Denies archives containing beyond 5000 discrete objects)
  - `MAX_TOTAL_SIZE = 500 * 1024 * 1024` (Triggers shutdown if aggregate physical size breaches 500 Megabytes)
  - `MAX_FILE_SIZE = 100 * 1024 * 1024` (Halts execution preventing any singular payload expanding further than 100MB)

### ✂️ Semantic NLP Chunk Limits
- **Target File**: `ragprep/core/chunk.py`
- Requires explicit tuning conforming directly to the Vector Model context window limits or Token maximums applied across Cloud Embeddings (e.g., OpenAI/Cohere). 
  - `target_len = 1000`: Mandates logical split logic executing only near English/Korean punctuation limits post 1000 aggregated characters.
  - `overlap_len = int(target_len * 0.15)`: Retains previous 150-character contextual footprints unifying severed sentences against conversational AI prompts.

### 💯 Heuristic Quality Gate Ratios
- **Target File**: `ragprep/core/quality.py`
- Calculates absolute boundaries forcing document segregation (`PASS`, `REVIEW`, `QUARANTINE`).
  - `short_ratio > 0.9` -> `REVIEW`: Identifies uncharacteristically fragmented sources; triggering if 90% of extracted subsets register under minimum acceptable lengths.
  - `meaningless_ratio > 0.6` -> `QUARANTINE`: Aggressively targets and ejects parsing disasters filled by HTML binary debris (`<>`, `\n`) exceeding a 60% contamination presence.

## 2. Infrastructure Environment Parameters

Deployments mandate server-level configuration variables guaranteeing performance bounds uninhibited by code execution logic. 

```bash
# Optional execution uniformity enforcing identical hashing sequences multi-process iterations
export PYTHONHASHSEED=0

# Mandated UNIX protection schema prohibiting "Other" external directory access vectors
umask 027
```
