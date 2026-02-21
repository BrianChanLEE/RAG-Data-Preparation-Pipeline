# Release Process

**Target Audience**: Release Engineers, Infrastructure SREs
**Objective**: Detach local execution logic translating codebases towards remote server integration staging protocols.

---

## 1. Versioning Architectures

Pipeline branches abide strictly towards `MAJOR.MINOR.PATCH` schemas:
- **MAJOR**: Re-engineering `ChunkSchema` models destroying backwards Vector Database integrations.
- **MINOR**: Implementing external options flag matrices (`--pii-mask`) unlocking secondary pipeline routes.
- **PATCH**: Micro-regulating Regex masking identifiers or addressing minor encoding fractures resolving broken parsers.

## 2. Deployment Life Cycles

Systems inherently target Linux-centric environments deploying under generic `systemd` cron schedulers.

1. **Repository Synchronization**
   ```bash
   git pull origin main
   git checkout tags/v1.2.0
   ```
2. **Dependency Harmonization**
   Aggressively patch security vulnerabilities ensuring all infrastructure bindings map explicitly against `requirements.txt` footprints.
   ```bash
   pip install --upgrade -r requirements.txt
   ```
3. **Schema Rollover Assertions**
   Developers modifying code structurally must correlate updating the global `SCHEMA_VERSION = "1.0"` integer inside `core/models.py`. Validated versions directly write against `manifest.json` ensuring perpetual audit lineage tracking.

## 3. Zero-Downtime Rollout Strategy

Although batch systems bypass inherent 24/7 web expectations, simultaneous script overlaps via cron invocations crash environments destructively. 

- **Migration**: Updating physical Python codes demands absolute hibernation validating previous `ragprep.prepare` routines terminated prior shifting scripts.
- Partial document failure traversing system swaps self-heals via Scanner detection logic demanding zero physical storage reversals upon subsequent cycles.
