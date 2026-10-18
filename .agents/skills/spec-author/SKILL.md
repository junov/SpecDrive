---
name: spec-author
description: >-
  Helps the user write, refine, or review Markdown specifications in a spec-as-source project
  (spec/, src/, test/). Use when the user asks to draft a new feature spec, add or change a
  requirement, turn an idea or bug report into spec text, or review/lint spec edits before
  syncing. Launches a parallel sub-agent to match requests against open project issues, confirms
  issue links with the user, proposes creating follow-up issues (with user confirmation),
  references linked issues and open-issue TODOs in the spec, and posts permission-gated
  investigation findings to issues. Produces spec text only and never edits src/ or test/; hand
  off to spec-sync for that.
---

# Spec Author

In this project the spec is the source code. Your job here is to help the user write spec text
that an agent can turn into tests and code **without guessing**. The user owns the spec: you
propose, they approve.

* Canonical format: [spec-format.md](references/spec-format.md). Read it before writing spec text.
* Review checklist: [quality-checklist.md](references/quality-checklist.md)
* Helper script: `scripts/specdrive.py`, run from the repo root as
  `python scripts/specdrive.py <command>` (or `python third_party/specdrive/scripts/specdrive.py <command>` in host projects).

## Issue Discovery, Linking, Follow-Up Issues & Investigation Comments

Whenever `spec-author` is invoked to draft, extend, or triage a request:

1. **Parallel Open-Issue Search (Sub-Agent)**:
   * **Skip Condition**: If the user **explicitly mentions an issue** in their prompt (e.g., `#123`, an issue URL, or an explicit issue identifier), **skip** searching for related issues and treat that issue as linked (fetching its details directly if helpful).
   * **Parallel Sub-Agent Launch**: Otherwise, immediately spawn a background sub-agent in parallel (`invoke_subagent`) while you read `spec/` files. Instruct the sub-agent to check open issues in the current project (for example, GitHub issues via `gh issue list --state open --json number,title,body,url,labels`, configured MCP issue trackers, or the repository remote from `git remote -v`) and return any open issues that may correspond to the user's request.
2. **Confirm Linked Issues or Propose New Issue(s)**:
   * **If candidate open issues are found**: Present them (issue number, title, and link) and **ask the user to confirm** which issue(s) should be linked to the current work (if any).
   * **If no associated issue exists** (or candidate issues were declined): Propose creating one or more new issues for the current work (showing proposed title/description).
   * **Proceeding without an issue is always an option**: Always offer the user the choice to proceed without an associated issue.
   * **Do not create an issue without confirmation**: Always obtain user confirmation before creating any new issue (e.g. via `gh issue create`). If the user chooses to proceed without an associated issue, respect that decision and proceed.
3. **Reference Linked Issues in the Spec**:
   * Wherever appropriate, reference confirmed linked issues in the requirement's `Notes:` line or section in `spec/` (e.g., `Notes: Linked to #42.`). If the user instructed to proceed without an issue, no issue reference is needed.
4. **Propose Creating Follow-Up Issues & Add `TODO` Comments (Confirmation Required)**:
   * When drafting or reviewing specs uncovers problems, deferred edge cases, or possible improvements that should be addressed in follow-up work, **propose creating a new issue** (for example on GitHub via `gh issue create`).
   * **Mandatory Confirmation Gate**: You **MUST** always ask the user for confirmation (showing the proposed issue title and description) before creating a new issue.
   * When appropriate, add `TODO` comments referencing open issues to `spec/` (e.g., `<!-- TODO(#45): ... -->` or a `TODO(#45)` note).
   * When updating a spec to address an issue that is now being fixed or is already closed, remove any `TODO` comments in `spec/` that reference that issue (it is fine to reference fixed or closed issues in normal comments or `Notes:`, just not in `TODO` comments).
5. **Post Investigation Findings to Linked Issues (Permission Required)**:
   * When investigating the request or bug uncovers important findings (root causes, protocol flaws, edge cases, or architectural constraints), propose posting a concise explanatory comment to the linked issue(s).
   * **Mandatory Permission Gate**: Before posting any comment to an issue, you **MUST** show the user the target issue and proposed comment content and ask for explicit permission. Never post a comment to an issue without the user's approval.

## Modes

### A. Draft or extend a feature
1. Unless the user already specified an issue in their prompt, launch the parallel issue-search sub-agent while reading `spec/product.md`, `spec/architecture.md`, and the target feature file if it exists.
2. If the request is vague, ask **at most 3–5 focused questions** in one batch, covering actors,
   triggers, limits, error behavior, and what's out of scope. Offer a recommended default for each.
   If candidate open issues were found by the sub-agent, ask the user to confirm which issue(s) to link (if any).
3. Write the requirements in the canonical format (EARS + Given/When/Then acceptance).
   * New feature file: pick a short uppercase `prefix`, put it in the front matter, and use the
     feature template from spec-format.md.
   * New IDs: run `specdrive.py next-id <PREFIX>` once per requirement, and edit the file between
     calls so that each call sees the previous ID. Never invent or reuse IDs by hand.
   * Reference any confirmed linked issue(s) in the requirement's `Notes:` section where appropriate, and remove any stale `TODO` comments in `spec/` for issues addressed by this change.
4. Run the quality checklist on what you wrote and fix your own BLOCKERs and WARNINGs.
5. If follow-up problems or improvements were identified, propose creating new issue(s) and ask the user for confirmation before creating them; once created, add `TODO` comments referencing the open follow-up issue(s) in `spec/` where appropriate.
6. If important findings were uncovered during investigation of a linked issue, ask the user for permission to post a summary comment to the issue.
7. Show the user the drafted text, or the diff if you edited the file, and point out the
   assumptions you made. **Stop there.** Implementation happens only when the user asks to
   sync (spec-sync skill).

### B. Review the user's own edits (pre-sync lint)
1. Run `specdrive.py delta` to see exactly what changed since the last sync.
2. Apply the checklist to every ADDED or MODIFIED requirement and to the
   "Per change" section for REMOVED and context changes.
3. Report findings grouped as BLOCKER / WARNING / NIT, each with a concrete replacement
   suggestion. Don't apply semantic changes without the user's approval.
4. If the review uncovers broader problems or follow-up improvements, propose creating new issue(s) (asking the user for confirmation first) and adding corresponding `TODO` comments in `spec/`. Also flag any `TODO` comments in `spec/` that reference already-fixed or closed issues so they are removed or converted to normal non-`TODO` references.
5. You **may** apply purely mechanical fixes without asking, but you must report them: assigning
   missing IDs via `next-id`, fixing heading syntax, or moving a requirement under `## Requirements`.

### C. Turn a bug report or code change request into spec text
1. Unless the user explicitly mentioned an issue in their prompt, launch the parallel issue-search sub-agent to check if the bug report or change request matches any open project issues, while finding the governing requirement(s) (`specdrive.py trace --id <ID>`, or search `spec/`).
2. If candidate open issues are found, ask the user to confirm which issue(s) should be linked (if any).
3. Decide which case applies:
   * **The spec is wrong or incomplete:** propose a MODIFIED or ADDED requirement (referencing confirmed linked issues in `spec/` where appropriate) and show the diff.
   * **The code violates a correct spec:** no spec edit is needed. Tell the user it's an
     implementation defect and use the spec-verify skill (bug triage) to fix it.
4. If follow-up problems or improvements are discovered during triage, propose creating new issue(s) and ask the user for confirmation before creating them.
5. When important root-cause or design findings are uncovered while investigating a linked issue, ask the user for permission before posting an explanatory comment to the issue.
6. Requests like "just change the code to do X" in a spec-as-source repo get translated into a
   spec edit first, unless the change has no observable behavior (a pure refactor).

## Rules
* Never edit `src/` or `test/` in this skill.
* Never renumber, reuse, or delete IDs to "tidy up". Removed IDs are retired forever.
* Keep requirement text implementation-agnostic unless the user explicitly wants a binding
  `Implementation constraint:`.
* Prefer small, reviewable spec edits. Suggest splitting a large change into several syncs.
* Always confirm with the user before linking discovered issues (unless explicitly mentioned by the user), **always** ask for confirmation before creating a new issue, and **always** ask for explicit permission before posting any comments to an issue.
* It is okay to reference fixed or closed issues in normal comments or `Notes:`, but never in `TODO` comments; remove `TODO` markers once the referenced issue is fixed.


