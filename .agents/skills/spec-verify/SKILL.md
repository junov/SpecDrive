---
name: spec-verify
description: >-
  Audits traceability between specifications, code, and tests, checks for spec drift,
  and triages bug reports against the specification. Use when the user asks to verify
  test coverage, audit requirement implementation status, check if the codebase matches the
  spec, investigate an apparent bug, or detect drift between spec/ and src/ or test/.
---

# Spec-Verify

The `spec-verify` skill audits the alignment between the Markdown specification (`spec/`), the implementation (`src/`), and test coverage (`test/`). It is also the diagnostic entry point for triaging bug reports and diagnosing code drift.

* **Spec Format Reference**: [spec-format.md](../spec-author/references/spec-format.md)
* **Helper Script**: `python scripts/specdrive.py <command>`

---

## Capabilities & Workflows

### 1. Traceability Audit, Coverage Reporting & `TODO` Validation
Run:
```bash
python scripts/specdrive.py trace
```
Or for a specific requirement:
```bash
python scripts/specdrive.py trace --id <ID>
```
Review the generated matrix:
- **Untested requirements**: Requirements present in `spec/` that have zero `@spec <ID>` tags in `test/`.
- **Untagged implementation**: Requirements with no `@spec <ID>` tags in `src/`.
- **Orphan tags**: Code or tests referencing an `@spec <ID>` that does not exist or was retired.

To run a strict pass/fail integrity check:
```bash
python scripts/specdrive.py check
```

Additionally, audit `TODO` comments across `spec/`, `src/`, and `test/`:
- Validate that `TODO` comments are removed once the referenced issue is fixed or closed.
- It is okay to reference fixed or closed issues in normal comments (e.g., `// @spec AUTH-002 (Issue #42)` or `Notes: Linked to #42.`), just **not** in `TODO` comments.

---

### 2. Code Drift Audit
To detect changes made directly to code without going through the specification:
```bash
python scripts/specdrive.py status
```
If the output lists modified or untracked files in `src/` or `test/` while a sync is NOT in progress:
1. Examine the diff of those files vs the baseline commit (`python scripts/specdrive.py base`).
2. If the code was changed to implement new behavior or fix a bug, inform the user:
   > In a spec-as-source project, behavioral changes must originate in `spec/`.
3. Offer to help reverse-engineer or backport those changes into the relevant `spec/` markdown files (using `spec-author`), then execute `spec-sync`.

---

### 3. Bug & Defect Triage
When a user reports a bug, defect, or unexpected behavior:

1. **Locate the Requirement & Check Open Issues**:
   - Search `spec/` for the feature or requirement governing the behavior.
   - Unless the user already specified an issue in their prompt or one was confirmed via `spec-author`, launch a parallel sub-agent to check whether the bug corresponds to any open issues in the project, and ask the user to confirm which issue(s) to link (if any).
   - If no requirement mentions the behavior $\rightarrow$ **Missing Spec**. Guide user to `spec-author` to draft a requirement.
2. **Inspect the Existing Spec**:
   - **Case A: The spec accurately describes the intended behavior.**
     - The implementation in `src/` is defective or a test in `test/` is missing/flawed.
     - Fix the code and ensure tests tagged with `@spec <ID>` (referencing any confirmed linked issue where appropriate, e.g., `// @spec <ID> (Issue #42)`) fail before the fix and pass after.
     - No spec changes needed.
   - **Case B: The spec specifies the wrong behavior or omitted an edge case.**
     - This is a specification bug.
     - Do not touch `src/` directly. Propose an updated requirement (`MODIFIED` or `ADDED`, referencing any confirmed linked issue in `Notes:`) using `spec-author`.
     - Once approved, run `spec-sync` to propagate the fix to code and tests.
   - **Case C: The spec is ambiguous or silent on the edge case.**
     - Ask the user for clarification with 2–3 concrete alternatives.
     - Update the spec with the chosen behavior, then sync.
3. **Post Investigation Findings to Linked Issues (Permission Required)**:
   - When investigating the bug uncovers important root-cause findings, prepare a concise comment explaining those findings for the linked issue(s).
   - **Mandatory Permission Gate**: Always show the proposed comment to the user and ask for explicit permission before posting any comment to an issue.

---

### 4. Regression & Verification Run
Run the full test suite as defined in `spec/architecture.md`:
```bash
# E.g. pytest, npm test, etc.
```
Correlate failures back to their `@spec <ID>` annotations to identify which requirement's contract was breached.
