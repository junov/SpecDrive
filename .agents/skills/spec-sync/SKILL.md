---
name: spec-sync
description: >-
  Synchronizes incremental Markdown specification edits into source code and tests.
  Use when the user has edited files under spec/ and wants to update the implementation,
  generate new code/tests, reconcile code with the spec, or accept a spec change.
  Enforces design document approval for complex/architectural syncs, presents synthesized
  code for user review, validates traceability and TODO hygiene, and commits the
  synchronization only after explicit user approval.
---

# Spec-Sync

The `spec-sync` skill is the core execution engine of the spec-as-source process. When a user modifies the Markdown specification in `spec/`, this skill detects the exact incremental requirements delta and compiles that delta into corresponding code and tests.

* **Detailed Protocol**: [sync-protocol.md](references/sync-protocol.md)
* **Spec Format Reference**: [spec-format.md](../spec-author/references/spec-format.md)
* **Helper Script**: `scripts/specdrive.py`, run from repository root as:
  `python scripts/specdrive.py <command>`

---

## Workflow Steps

### 1. Inspect Delta & Verify Spec Approval
Always start by checking the current state against the last sync commit:
```bash
python scripts/specdrive.py delta
python scripts/specdrive.py status
```
- If there are duplicate IDs or headings missing IDs under `## Requirements`, resolve them before proceeding.
- If no baseline exists, this is **initial generation** (all requirements are `ADDED`).
- If code drift exists in `src/` or `test/` from edits outside a sync, review those changes so intentional modifications are preserved or reflected back into `spec/`.
- **Verify Spec Review Gate**: Confirm that the user has reviewed and approved the spec changes being synchronized. If the user has not yet reviewed the spec delta, prompt them to review before proceeding.

### 2. Plan the Incremental Updates & Check Associated Issues
Formulate a concise step-by-step plan:
1. **Tests to add/update/delete** in `test/` (keyed by requirement ID).
2. **Components/modules to touch** in `src/`.
3. Check `spec/architecture.md` for technology stack, coding conventions, and test commands.
4. **Associated Issue Check**:
   - Check if the current work has an associated issue (e.g., referenced in `spec/` requirement `Notes:`, or specified by the user).
   - If the current work does **not** have an associated issue:
     - **Do not ask again if already decided**: If the user already instructed the `spec-author` skill to proceed with the current work without an associated issue, **do not ask the user again**.
     - Otherwise (e.g., `spec-sync` was invoked directly on spec edits authored outside `spec-author`), propose creating one or more new issues for the current work.
     - **Proceeding without an associated issue is always an option**: Always offer the user the choice to proceed without an associated issue.
     - **Mandatory Confirmation Gate**: Never create an issue without explicit user confirmation.

### 2b. Design Document & Approval Gate (Complex or Architectural Syncs)
Evaluate the scope and complexity of the required changes:
1. **Determine Complexity**:
   - **Complex or Architectural**: The change modifies `spec/architecture.md`, introduces new services/modules/subsystems, alters data storage schemas or communication protocols, refactors multiple interdependent modules, or introduces non-trivial system design decisions.
   - **Simple / Localized**: The change is a localized bug fix, a straightforward field/method addition, a minor UI tweak, or an isolated logic refinement that does not alter system architecture or design patterns.
2. **Action for Complex or Architectural Syncs**:
   - **Produce a Design Document**: Generate a design document (as an artifact or detailed markdown document) detailing:
     - Architectural approach, component interactions, and data flow.
     - New or modified interfaces, data contracts, and schema changes.
     - Concrete file modification map across `src/` and `test/`.
     - Key trade-offs, potential risks, and alternatives considered.
   - **Mandatory Design Approval Gate**: **STOP and present the design document to the user. You MUST obtain explicit user approval on the design document before proceeding to Step 3 or writing any code or tests.**
3. **Action for Simple Code Changes**:
   - For simple code changes that do not affect architecture and do not require system design changes, bypass the design approval step, explicitly inform the user that design approval is bypassed, and proceed directly to Step 3.

### 3. Generate & Update Tests First (`test/`)
For each changed requirement:
- **`ADDED`**: Write new unit/integration tests directly derived from the requirement's `Acceptance:` criteria. Tag each test function with `# @spec <ID>` (or language-appropriate comment), and include any linked issue references from the spec where appropriate (e.g., `// @spec <ID> (Issue #42)`).
- **`MODIFIED`**: Update existing tests tagged with `@spec <ID>` to match the revised acceptance criteria, preserving or adding any linked issue references.
- **`REMOVED`**: Remove or retire tests associated with the removed ID.
- When appropriate, add `TODO` comments referencing open follow-up issues in `test/` (e.g., `// TODO(#45): ...`).

### 4. Implement Code Changes (`src/`) & Propose Follow-Up Issues
- Update only the source files necessary to satisfy the new or modified requirements.
- Never write extra or speculative code beyond what is specified in `spec/`.
- Tag primary implementing functions, classes, or endpoints with `@spec <ID>` (and any linked issue reference where appropriate).
- **Propose Creating Follow-Up Issues (Confirmation Required)**:
   - If synthesizing or testing the changes uncovers problems, technical debt, or possible improvements that should be addressed in follow-up work, **propose creating a new issue** (for example on GitHub via `gh issue create`).
   - **Mandatory Confirmation Gate**: You **MUST** always ask the user for confirmation (presenting the proposed title and description) before creating a new issue.
   - Once confirmed and created, add `TODO` comments referencing the open issue to `spec/`, `src/`, and/or `test/` where appropriate (e.g., `// TODO(#45): ...`).
- If important technical findings were uncovered during implementation or investigation of a linked issue, ask the user for explicit permission before posting an explanatory comment to the issue.

### 5. Run Tests
Execute the project's test command as defined in `spec/architecture.md` (e.g. `pytest`, `npm test`, `cargo test`, `go test`).
- Ensure all tests pass with zero regressions.
- If tests fail, fix the implementation or test. If the spec is contradictory, consult the user.

### 6. Verify Traceability & Issue `TODO` Hygiene
Run:
```bash
python scripts/specdrive.py check
```
Verify that:
- Every requirement in `spec/` has test coverage.
- No orphan `@spec <ID>` tags exist in `src/` or `test/`.
- **Validate `TODO` Comments**: Inspect `TODO` comments across `spec/`, `src/`, and `test/` and verify that any `TODO` comments referencing an issue that is now fixed or closed have been removed (or converted to normal non-`TODO` comments). It is okay to reference fixed or closed issues in regular comments (e.g., `// @spec AUTH-002 (Issue #42)`), just **not** in `TODO` comments.

### 7. Code Review & Approval Gate
Present a concise summary of the synthesized code, created/modified tests, diffs, and test runner results to the user.

**Mandatory Code Review Gate**: Ask the user to review and approve the synthesized code and tests before advancing the baseline:
- **If approved**: Proceed to Step 8.
- **If the user provides feedback**:
  - Determine whether the feedback justifies a modification to the spec.
  - If spec changes are required, hand off to the `spec-author` skill and inform the user to re-invoke `spec-sync` after reviewing and approving the updated spec.
  - Otherwise (no spec modification required), return to Step 2 and iterate on the implementation/tests taking the user's feedback into account.
- **If the user cancels the sync**: Revert uncommitted changes in `src/` and `test/` (e.g., `git restore src/ test/` and remove untracked generated files) to return to a clean baseline state.

### 8. Accept the Sync (Explicit User Approval Required)
**`specdrive accept` MUST NEVER be run without explicit user approval.**
Only once all tests pass, traceability passes, and the user has explicitly confirmed approval:
```bash
python scripts/specdrive.py accept -m "<Brief summary of changes>"
```
This automatically stages `spec/`, `src/`, `test/` and records a git commit with `Spec-Sync:` trailers. This commit becomes the new baseline.

### 9. Propose Submission (`spec-submit`)
After the sync commit is recorded, **propose proceeding with the `spec-submit` skill to the user** (do not execute it automatically):
- Ask the user if they would like to submit the committed changes upstream using `spec-submit`.
- Explain what `spec-submit` will do:
  - Push committed changes to the upstream remote.
  - Close completely fixed issues (or annotate the Pull Request / code review with `Closes #123` so issues close automatically on merge).
  - Update fixed issues with `"Fixed in release <version>"` whenever release tags are pushed or merged.
- Only invoke or proceed with `spec-submit` once the user confirms.
