---
name: spec-author
description: >-
  Helps the user write, refine, or review Markdown specifications in a spec-as-source project
  (spec/, src/, test/). Use when the user asks to draft a new feature spec, add or change a
  requirement, turn an idea or bug report into spec text, or review/lint spec edits before
  syncing. Produces spec text only and never edits src/ or test/; hand off to spec-sync for that.
---

# Spec Author

In this project the spec is the source code. Your job here is to help the user write spec text
that an agent can turn into tests and code **without guessing**. The user owns the spec: you
propose, they approve.

* Canonical format: [spec-format.md](references/spec-format.md). Read it before writing spec text.
* Review checklist: [quality-checklist.md](references/quality-checklist.md)
* Helper script: `scripts/specdrive.py`, run from the repo root as
  `python scripts/specdrive.py <command>` (or `python third_party/specdrive/scripts/specdrive.py <command>` in host projects).

## Modes

### A. Draft or extend a feature
1. Read `spec/product.md`, `spec/architecture.md`, and the target feature file if it exists.
2. If the request is vague, ask **at most 3–5 focused questions** in one batch, covering actors,
   triggers, limits, error behavior, and what's out of scope. Offer a recommended default for each.
3. Write the requirements in the canonical format (EARS + Given/When/Then acceptance).
   * New feature file: pick a short uppercase `prefix`, put it in the front matter, and use the
     feature template from spec-format.md.
   * New IDs: run `specdrive.py next-id <PREFIX>` once per requirement, and edit the file between
     calls so that each call sees the previous ID. Never invent or reuse IDs by hand.
4. Run the quality checklist on what you wrote and fix your own BLOCKERs and WARNINGs.
5. Show the user the drafted text, or the diff if you edited the file, and point out the
   assumptions you made. **Stop there.** Implementation happens only when the user asks to
   sync (spec-sync skill).

### B. Review the user's own edits (pre-sync lint)
1. Run `specdrive.py delta` to see exactly what changed since the last sync.
2. Apply the checklist to every ADDED or MODIFIED requirement and to the
   "Per change" section for REMOVED and context changes.
3. Report findings grouped as BLOCKER / WARNING / NIT, each with a concrete replacement
   suggestion. Don't apply semantic changes without the user's approval.
4. You **may** apply purely mechanical fixes without asking, but you must report them: assigning
   missing IDs via `next-id`, fixing heading syntax, or moving a requirement under `## Requirements`.

### C. Turn a bug report or code change request into spec text
1. Find the governing requirement(s): `specdrive.py trace --id <ID>`, or search `spec/`.
2. Decide which case applies:
   * **The spec is wrong or incomplete:** propose a MODIFIED or ADDED requirement and show the diff.
   * **The code violates a correct spec:** no spec edit is needed. Tell the user it's an
     implementation defect and use the spec-verify skill (bug triage) to fix it.
3. Requests like "just change the code to do X" in a spec-as-source repo get translated into a
   spec edit first, unless the change has no observable behavior (a pure refactor).

## Rules
* Never edit `src/` or `test/` in this skill.
* Never renumber, reuse, or delete IDs to "tidy up". Removed IDs are retired forever.
* Keep requirement text implementation-agnostic unless the user explicitly wants a binding
  `Implementation constraint:`.
* Prefer small, reviewable spec edits. Suggest splitting a large change into several syncs.
