---
name: spec-sync
description: >-
  Synchronizes incremental Markdown specification edits into source code and tests.
  Use when the user has edited files under spec/ and wants to update the implementation,
  generate new code/tests, reconcile code with the spec, or accept a spec change.
  Computes the spec delta against the git baseline, updates test/ and src/, runs validation,
  and commits the synchronization.
---

# Spec-Sync

The `spec-sync` skill is the core execution engine of the spec-as-source process. When a user modifies the Markdown specification in `spec/`, this skill detects the exact incremental requirements delta and compiles that delta into corresponding code and tests.

* **Detailed Protocol**: [sync-protocol.md](references/sync-protocol.md)
* **Spec Format Reference**: [spec-format.md](../spec-author/references/spec-format.md)
* **Helper Script**: `scripts/specdrive.py`, run from repository root as:
  `python scripts/specdrive.py <command>`

---

## Workflow Steps

### 1. Inspect Delta & Status
Always start by checking the current state against the last sync commit:
```bash
python scripts/specdrive.py delta
python scripts/specdrive.py status
```
- If there are duplicate IDs or headings missing IDs under `## Requirements`, resolve them before proceeding.
- If no baseline exists, this is **initial generation** (all requirements are `ADDED`).
- If code drift exists in `src/` or `test/` from edits outside a sync, review those changes so intentional modifications are preserved or reflected back into `spec/`.

### 2. Plan the Incremental Updates
Formulate a concise step-by-step plan:
1. **Tests to add/update/delete** in `test/` (keyed by requirement ID).
2. **Components/modules to touch** in `src/`.
3. Check `spec/architecture.md` for technology stack, coding conventions, and test commands.

### 3. Generate & Update Tests First (`test/`)
For each changed requirement:
- **`ADDED`**: Write new unit/integration tests directly derived from the requirement's `Acceptance:` criteria. Tag each test function with `# @spec <ID>` (or language-appropriate comment).
- **`MODIFIED`**: Update existing tests tagged with `@spec <ID>` to match the revised acceptance criteria.
- **`REMOVED`**: Remove or retire tests associated with the removed ID.

### 4. Implement Code Changes (`src/`)
- Update only the source files necessary to satisfy the new or modified requirements.
- Never write extra or speculative code beyond what is specified in `spec/`.
- Tag primary implementing functions, classes, or endpoints with `@spec <ID>`.

### 5. Run Tests
Execute the project's test command as defined in `spec/architecture.md` (e.g. `pytest`, `npm test`, `cargo test`, `go test`).
- Ensure all tests pass with zero regressions.
- If tests fail, fix the implementation or test. If the spec is contradictory, consult the user.

### 6. Verify Traceability
Run:
```bash
python scripts/specdrive.py check
```
Verify that:
- Every requirement in `spec/` has test coverage.
- No orphan `@spec <ID>` tags exist in `src/` or `test/`.

### 7. Get User Approval
Present a concise summary of the synthesized code, created/modified tests, and test runner results. 
In the case of UI changes, display before and after screenshots that illustrate the changes.

> **IMPORTANT**:
> Never show generated images or mockups instead of actual screenshots. If you don't know how to generate the correct real screenshots then don't show any. 

Ask the User to provide feedback, approve the changes, or cancel the sync:
- **If approved**: Proceed to Step 8.
- **If the user provides feedback**:
  - Determine whether the feedback justifies a modification to the spec.
  - If spec changes are required, hand off to the `spec-author` skill and inform the user to re-invoke `spec-sync` after approving the updated spec.
  - Otherwise (no spec modification required), return to Step 2 and iterate on the implementation/tests taking the user's feedback into account.
- **If the user cancels the sync**: Revert uncommitted changes in `src/` and `test/` (e.g., `git restore src/ test/` and remove untracked generated files) to return to a clean baseline state.

### 8. Accept the Sync
Once all tests pass, traceability passes, and user has approved:
```bash
python scripts/specdrive.py accept -m "<Brief summary of changes>"
```
This automatically stages `spec/`, `src/`, `test/` and records a git commit with `Spec-Sync:` trailers. This commit becomes the new baseline.
