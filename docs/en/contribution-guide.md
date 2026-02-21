# Contribution Guide

**Target Audience**: Open-source Advocates, Enterprise Internal Teams
**Objective**: Outlining the stringent protocols regulating merge requests maintaining structural pipeline infallibility.

---

## 1. Syntax Convention

This pipeline actively dictates robust paradigms mandating comprehensive maintainability checks.
- **Python Limit**: Baseline `3.10` Required.
- **Type Hinting**: All logic functions demand exhaustive DTO annotations (`-> bool`, `ctx: RunContext`).
- **Standard Formatting**: Enforced formatting methodologies matching `Black` (4 space indents) layered against rigorous `flake8` regression checks.

## 2. Incorporating Novel Extractor Archetypes

Enhancing capabilities capturing unrecognized syntaxes (`.docx`, `.csv`) mandates preserving isolation logics.

1. Construct independent schemas named `ragprep/core/extract_{format}.py`.
2. Restrict internal dependencies utilizing exclusively `FileMeta` contexts decoupled against extraneous systems.
3. Enforce deterministic returns utilizing explicitly sanitized JSON layouts routing output directly against specific `ctx.dirs['extracted']` environments carrying strictly `True/False` health signatures.
4. Establish logical routing trees amending the central `ragprep/core/router.py` framework matching the distinct parser.

## 3. Merge Criteria Prerequisites

Protecting operational RAG boundaries heavily outweighs accelerated feature pipelines.

- Validating Data Type Schema modification requires a mandatory upgrade advancing the `SCHEMA_VERSION` tracker.
- Pull Requests demand regression assurance tests validating the native suite against `-m ragprep.prepare --force` appending historical execution timelines protecting previous extraction logics.
- Refrain from committing unvetted external python dependencies attached to `requirements.txt` aiming to achieve absolute `Zero-external-dependency` isolation policies favoring Standard Library infrastructures.
