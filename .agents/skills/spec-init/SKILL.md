---
name: spec-init
description: >-
  Scaffolds a new project or bootstraps an existing codebase into a SpecDrive
  spec-as-source architecture (spec/, src/, test/). Use when the user asks to
  initialize a new spec-driven project, set up the spec/src/test directory layout,
  or bootstrap specifications for an existing project.
---

# Spec-Init

The `spec-init` skill sets up the foundation for a spec-as-source project. It initializes the folder structure, configures the baseline specifications, ensures Git is properly set up, and records the initial synchronization baseline.

* **Spec Format Reference**: [spec-format.md](../spec-author/references/spec-format.md)
* **Helper Script**: `python .agents/skills/spec-sync/scripts/specdrive.py <command>`

---

## Initialization Workflows

### Mode A: Greenfield Project Setup

When starting a project from scratch:

1. **Verify or Initialize Git**:
   ```bash
   git status
   # If not a repo:
   git init
   ```
2. **Create Core Folders**:
   ```bash
   python .agents/skills/spec-sync/scripts/specdrive.py init
   ```
   This ensures `spec/`, `src/`, and `test/` directories exist, and creates `spec/features/`.

3. **Scaffold Foundational Specs**:
   Create standard context files in `spec/`:
   - `spec/product.md`: High-level vision, target users, problem statement, core capabilities, and domain glossary.
   - `spec/architecture.md`: Language, runtime, framework choices, directory layout within `src/` and `test/`, coding style, and explicit commands for building, running, and testing.

4. **Draft the First Capability**:
   Create `spec/features/<feature-name>.md` with a chosen uppercase prefix (e.g. `CORE`, `AUTH`, `API`), containing the first set of functional requirements formatted with EARS patterns and Given/When/Then acceptance criteria.
   Use `python .agents/skills/spec-sync/scripts/specdrive.py next-id <PREFIX>` to allocate IDs.

5. **Initial Baseline Commit**:
   Commit the initial spec structure as the foundational baseline:
   ```bash
   git add spec
   python .agents/skills/spec-sync/scripts/specdrive.py accept -m "Initial specification baseline"
   ```

---

### Mode B: Brownfield / Existing Codebase Bootstrapping

When introducing SpecDrive to an existing codebase:

1. **Inspect Existing Project**:
   - Detect language, framework, dependencies (e.g. `package.json`, `pyproject.toml`, `Cargo.toml`).
   - Identify existing test runners and entry points.
2. **Reorganize or Symlink to Canonical Layout**:
   - Ensure `src/` houses implementation and `test/` houses tests.
   - Create `spec/` and `spec/features/`.
3. **Generate `spec/architecture.md`**:
   - Document the current tech stack, directory conventions, and exact test execution commands.
4. **Draft Reverse-Engineered Feature Specs**:
   - Group existing capabilities into feature specs in `spec/features/*.md`.
   - Assign requirement IDs (`AUTH-001`, `DATA-001`, etc.) to distinct behaviors verified by existing tests.
   - Annotate existing tests with `# @spec <ID>` (or language comment equivalent).
5. **Establish Baseline**:
   Run `specdrive.py check` to verify initial traceability, then:
   ```bash
   python .agents/skills/spec-sync/scripts/specdrive.py accept -m "Adopt SpecDrive spec-as-source baseline"
   ```
