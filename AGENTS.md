# SpecDrive Agent Guidelines (Always Active)

This project operates on the **Spec-as-Source** paradigm. In this repository, **specifications written in Markdown are the source code**, while files in `src/` and `test/` are derived implementation artifacts maintained by AI agents.

---

## 1. Top-Level Folder Roles

- **`spec/`**: **The Single Source of Truth.**
  - `product.md`: Domain context, target users, glossary.
  - `architecture.md`: Binding architectural constraints, tech stack, conventions, and test commands.
  - `features/*.md`: Functional capability specifications with structured requirements and acceptance criteria.
  - **Humans primarily author and edit files here.**
- **`src/`**: Derived production code. Generated and maintained by AI agents to satisfy `spec/`.
- **`test/`**: Derived test suites. Generated and maintained by AI agents directly from `spec/` acceptance criteria.

---

## 2. Core Operational Rules for Agents

1. **Never edit `src/` to change behavior without updating `spec/` first**:
   If the user asks for a new feature, a behavior change, or an altered business rule, guide the user to update `spec/` (using the `spec-author` skill) or draft the spec changes for them. Then synchronize the changes into `src/` and `test/` (using the `spec-sync` skill).
2. **Traceability via `@spec <ID>`**:
   Every requirement in `spec/` has a unique, permanent identifier (`PREFIX-NNN`, e.g. `AUTH-001`).
   - Every test verifying a requirement MUST contain `@spec <ID>` in its name, docstring, or comment.
   - Every primary implementing component in `src/` should include `@spec <ID>`.
3. **No Unspecified Code**:
   Do not add features, endpoints, speculative configurations, or behavior not defined in `spec/`.
4. **Git-Native Synchronization**:
   Synchronization baseline commits are tagged with `Spec-Sync:` Git trailers.
   Use the Python helper script `scripts/specdrive.py` (or `third_party/specdrive/scripts/specdrive.py` in host projects) to calculate deltas, trace requirements, verify coverage, and accept syncs:
   - `python scripts/specdrive.py status`: Check pending changes and code drift.
   - `python scripts/specdrive.py delta`: Inspect requirement-level changes vs baseline.
   - `python scripts/specdrive.py trace`: View the traceability matrix.
   - `python scripts/specdrive.py check`: Run automated validation checks.
   - `python scripts/specdrive.py accept -m "<msg>"`: Commit synchronized changes.

## 3. Skill Dispatch Guide

- **`spec-init`**: Use when bootstrapping a project into SpecDrive—either creating a brand-new software product from scratch (conducting a discovery interview, scoping the walking skeleton, and synthesizing initial code/tests) or adopting SpecDrive in an existing codebase.
- **`spec-author`**: Use when drafting, editing, or refining Markdown requirements, or converting ideas into specs. (Produces spec edits only; never touches `src/` or `test/`).
- **`spec-sync`**: Use when the user has edited `spec/` and wants the changes transformed into code and tests.
- **`spec-verify`**: Use when auditing test coverage, checking for code drift, or triaging whether a bug is a spec bug vs an implementation bug.
