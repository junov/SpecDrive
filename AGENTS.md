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
   If the user asks for a new feature, a behavior change, or an altered business rule, guide the user to update `spec/` (using the `spec-author` skill) or draft the spec changes for them.
2. **Mandatory Human-in-the-Loop Gates (Never Progress Automatically Across Stages)**:
   The SpecDrive process enforces strict human-in-the-loop review and approval gates between lifecycle steps:
   - **Gate A — Spec Review Gate (Before Sync)**:
     When spec changes are drafted or updated (via `spec-author` or during bug triage), the agent **MUST STOP** and present the spec diff and assumptions to the user. The agent **must never automatically progress to `spec-sync` or edit code**. The user must review and approve the spec changes before synchronization begins.
   - **Gate B — Design Document & Approval Gate (For Complex or Architectural Sync Steps)**:
     When a synchronization step requires complex business logic or architectural changes (e.g., changes affecting `spec/architecture.md`, system design, new subsystems/modules, major data schema or interface shifts), the agent **MUST produce a design document** (such as an artifact or markdown proposal) explaining the architecture, components, data flow, and file impacts, and **obtain explicit user approval before writing code or tests**.
     For simple code changes that do not affect architecture and do not require system design changes, the agent may bypass design approval and proceed directly to test and code implementation.
   - **Gate C — Code Review & Approval Gate (Before Accept)**:
     After tests and code are synthesized, tests pass, and `specdrive check` verifies traceability, the agent **MUST STOP** and present a clear summary of the synthesized code, created/modified tests, and diffs. The user must be given the opportunity to review and approve the code changes.
   - **Gate D — Accept Never Run Without Explicit User Approval**:
     The `accept` step (`specdrive accept` / `specnovel accept`) **MUST NEVER be run without explicit user approval**.
3. **Traceability via `@spec <ID>`**:
   Every requirement in `spec/` has a unique, permanent identifier (`PREFIX-NNN`, e.g. `AUTH-001`).
   - Every test verifying a requirement MUST contain `@spec <ID>` in its name, docstring, or comment.
   - Every primary implementing component in `src/` should include `@spec <ID>`.
4. **No Unspecified Code**:
   Do not add features, endpoints, speculative configurations, or behavior not defined in `spec/`.
5. **Git-Native Synchronization**:
   Synchronization baseline commits are tagged with `Spec-Sync:` Git trailers.
   Use the Python helper script `scripts/specdrive.py` (or `third_party/specdrive/scripts/specdrive.py` in host projects) to calculate deltas, trace requirements, verify coverage, and accept syncs:
   - `python scripts/specdrive.py status`: Check pending changes and code drift.
   - `python scripts/specdrive.py delta`: Inspect requirement-level changes vs baseline.
   - `python scripts/specdrive.py trace`: View the traceability matrix.
   - `python scripts/specdrive.py check`: Run automated validation checks.
   - `python scripts/specdrive.py accept -m "<msg>"`: Commit synchronized changes (requires explicit user approval).
6. **Deep Module Architecture & Seam Discipline**:
   Code generated in `src/` and tests in `test/` must embody **deep modules**: substantial behavior behind small interfaces placed at clean seams.
   - **Vocabulary**: *Module*, *Interface*, *Implementation*, *Depth*, *Seam*, *Adapter*, *Leverage*, *Locality*. (Avoid vague substitutes like "component," "service," or "boundary.")
   - **Design for Testability**: Accept dependencies rather than instantiating them inside; return computed results rather than mutating external state; keep interfaces small.
   - **The Interface is the Test Surface**: Tests verify observable behavior across the module seam; never couple tests to internal seams or private implementation details. Follow "replace, don't layer" testing.
   - **Seam Discipline**: "One adapter means a hypothetical seam; two adapters means a real one." Avoid speculative abstractions. Categorize dependencies (in-process, local-substitutable, remote-owned ports/adapters, true external).

---

## 3. Skill Dispatch Guide

- **`spec-init`**: Use when bootstrapping a project into SpecDrive—either creating a brand-new software product from scratch (conducting a discovery interview, scoping the walking skeleton, and synthesizing initial code/tests) or adopting SpecDrive in an existing codebase.
- **`spec-author`**: Use when drafting, editing, or refining Markdown requirements, or converting ideas into specs. Produces spec edits only, presents them for user review, and stops; never touches `src/` or `test/` and never automatically triggers `spec-sync`.
- **`spec-sync`**: Use when the user has reviewed and approved spec edits and wants the changes transformed into code and tests. Enforces design document approval for complex/architectural changes, presents synthesized code for user review, and requires explicit user approval before running `accept`.
- **`spec-verify`**: Use when auditing test coverage, checking for code drift, or triaging whether a bug is a spec bug vs an implementation bug.
- **`spec-submit`**: The final step of the SpecDrive process. Use when pushing committed changes to the upstream remote, closing completely fixed issues, configuring code reviews / pull requests with issue-closing annotations (e.g. 'Closes #123'), and commenting 'Fixed in release <version>' on fixed issues when release tags are pushed or merged.
