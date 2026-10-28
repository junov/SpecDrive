# Spec quality checklist

Run through this list whenever you draft a requirement or review a user's spec edit. Report
findings as concrete, quotable suggestions. Never silently rewrite the user's intent.

## Per requirement
- [ ] Has a valid, unique, never-before-used ID (`PREFIX-NNN`) and a short, specific title.
- [ ] States one observable behavior using an EARS pattern (WHEN / WHILE / IF-THEN / WHERE / SHALL).
- [ ] Has Given/When/Then acceptance criteria that are concrete enough to code as tests without
      guessing (inputs, expected outputs, messages, status codes, limits, timings).
- [ ] Covers the unhappy path(s): invalid input, unauthorized, not found, limits, timeouts, duplicates.
- [ ] No weasel words: *fast, easy, user-friendly, robust, appropriate, etc., and/or, as needed,
      support, handle, should probably*. Replace each with a measurable statement or remove it.
- [ ] No hidden implementation choices unless they're intentional (mark them as `Implementation constraint:`).
- [ ] Doesn't contradict another requirement, `architecture.md`, or the glossary.
- [ ] Uses glossary terms consistently (same name for the same concept everywhere).
- [ ] **Deep interface**: Defines high leverage behind a small interface (few methods/endpoints, simple parameters), avoiding shallow pass-through layers.
- [ ] **Seam placement**: Focuses requirements on the module's observable external interface/seam; does not dictate internal implementation seams or leak private module structure.
- [ ] **Testability**: Acceptance criteria specify inputs and observable return values/outcomes rather than hidden internal mutations.
- [ ] **Dependency category**: Dependencies conform to the 4 categories (in-process, local-substitutable, remote-owned ports/adapters, true external).

## Per change (delta review before syncing)
- [ ] Is each MODIFIED requirement still the same intent? If not, suggest REMOVED + ADDED with a new ID.
- [ ] Does a REMOVED requirement leave others dangling (references, flows, data no longer produced)?
- [ ] Does a context change (glossary, data model, architecture) silently change behavior of
      requirements that weren't edited? List them.
- [ ] **The deletion test**: Does the module or capability earn its keep? (If deleted, does complexity reappear across callers, or does it just remove an empty pass-through layer?)
- [ ] **Seam discipline**: Avoids premature abstraction—no port/interface is introduced with only one single adapter.
- [ ] Are new open questions blocking any ADDED or MODIFIED requirement?
- [ ] Is the change small enough to review? Suggest splitting large edits into several syncs.

## Severity labels for findings
- **BLOCKER**: the sync can't produce correct code (ambiguity, contradiction, missing ID).
- **WARNING**: likely to produce wrong or fragile behavior (missing error case, vague criterion, shallow pass-through).
- **NIT**: style or consistency.
