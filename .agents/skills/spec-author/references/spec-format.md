# SpecDrive spec format (canonical reference)

Every SpecDrive skill depends on this format. The helper script
(`scripts/specdrive.py`) parses it, so the **structural rules** below are
mandatory. The **style rules** are strong guidance.
For architectural principles and module design vocabulary, see [codebase-design.md](codebase-design.md).

## Project layout

```text
<repo>/
├── spec/                    # SOURCE OF TRUTH - humans edit this
│   ├── product.md           # vision, users, scope, glossary            (context)
│   ├── architecture.md      # stack, layout, conventions, commands, NFRs (context, binding)
│   └── features/
│       └── <capability>.md  # requirements live here, one file per capability
├── src/                     # derived: generated/maintained by the agent (deep modules)
├── test/                    # derived: generated/maintained by the agent (tests at seams)
└── AGENTS.md                # always-on rule telling agents this is a spec-as-source repo
```

Extra folders under `spec/` (e.g. `spec/api/`, `spec/data/`) are fine. Every `*.md` file under
`spec/` is parsed.

## Two kinds of sections

| Kind | How it's recognized | Delta key | Effect of a change |
|------|---------------------|-----------|--------------------|
| **Requirement** | Heading whose text starts with an ID: `### AUTH-003: Lock account after failed logins` | the ID | Targeted: tests + code for that ID |
| **Context** | Any other heading (`## Overview`, `## Data model`, all of `architecture.md`) | `file::Heading > Path` | Judgment call: may affect many requirements |

### Requirement rules (structural)

* **ID format:** `PREFIX-NNN`, which is uppercase letters/digits, a dash, and at least 3 digits
  (`AUTH-001`, `CART-042`, `NFR-007`). Use one prefix per feature file, declared in the front matter.
* **Heading:** `ID: Title`. The separator may be `:`, `.`, or `-`. Any heading level works, but
  `###` under `## Requirements` is the convention.
* **Extent:** a requirement section includes everything up to the next heading of the **same or
  higher** level. Deeper sub-headings (for example `#### Acceptance`) belong to it.
* **Permanence:** IDs are never renumbered or reused. Every ID that ever appeared in git history is
  retired. Get new IDs with `python scripts/specdrive.py next-id PREFIX`.
* **Identity = intent.** Rewording or tightening a requirement keeps its ID (MODIFIED). If the
  behavior changes into something different in kind, remove the old ID and add a new one.
* A heading directly under a `## Requirements` heading that has **no ID** is flagged as an
  *unidentified requirement*, and the sync won't be accepted until it gets one.

### Context rules

* Context sections apply globally. `architecture.md` is **binding**: language, frameworks, folder
  layout of `src/` and `test/`, module boundaries and seams, dependency categorization, coding conventions, and the build/test/lint commands.
* A context section changes whenever any line in it changes. Its key is the heading path, so
  renaming a heading looks like REMOVED + ADDED.
* Context sections may contain IDs for cross-cutting requirements (`NFR-001: p95 latency < 200 ms`).
  They then behave like requirements.

## Feature file template

```markdown
---
prefix: AUTH
status: active
---
# Authentication

## Overview
Why this capability exists, who uses it, and key flows. Context: not directly tested.

## Definitions
- **Session**: a server-side record binding a browser to a user, valid 30 days.

## Requirements

### AUTH-001: Sign in with email and password
WHEN a registered user submits a correct email and password,
THE SYSTEM SHALL start a session and redirect to `/dashboard`.

Acceptance:
- Given user `ann@example.com` with password `s3cret!`, when she signs in with those
  credentials, then a session cookie is set and the response redirects to `/dashboard`.
- Given the same user, when the password is wrong, then the response is 401 with the
  message "Email or password is incorrect" and no cookie is set.

### AUTH-002: Lock account after repeated failures
IF a user fails to sign in 5 times within 15 minutes,
THEN THE SYSTEM SHALL reject further attempts for that account for 15 minutes.

Acceptance:
- Given 5 failed attempts in 10 minutes, when a 6th attempt uses the correct password,
  then the response is 423 "Account temporarily locked".
- Given a lock that started 15 minutes ago, when the user signs in correctly, then sign-in succeeds.

Notes: Rationale and links. Non-binding unless phrased as SHALL.

## Out of scope
- Social login (planned for a later release).

## Open questions
- Should lockout also notify the user by email?   <!-- not implemented until resolved -->
```

## Style rules (EARS + acceptance criteria)

Write each requirement as one or more **EARS** statements (Easy Approach to Requirements Syntax):

| Pattern | Template |
|---------|----------|
| Ubiquitous | THE SYSTEM SHALL <response> |
| Event-driven | WHEN <trigger>, THE SYSTEM SHALL <response> |
| State-driven | WHILE <state>, THE SYSTEM SHALL <response> |
| Unwanted behavior | IF <condition>, THEN THE SYSTEM SHALL <response> |
| Optional feature | WHERE <feature is enabled>, THE SYSTEM SHALL <response> |
| Complex | WHILE <state>, WHEN <trigger>, THE SYSTEM SHALL <response> |

Then list **Acceptance** criteria as Given/When/Then bullets. **They are the test oracle:** each
bullet becomes at least one test, and nothing untestable belongs in them.

* One behavior per requirement. If a requirement needs "and also", split it.
* Use concrete values: limits, formats, messages, status codes, and time windows.
* Cover the unhappy paths: invalid input, missing data, permissions, concurrency, limits.
* **Specify observable behavior at the seam, not internal mechanics**: Say WHAT is observable across
  the module's external interface, not HOW it is partitioned internally. The *how* (technology choices,
  seams, dependency categories) goes in `architecture.md`, or in an explicit `Implementation constraint:`
  line inside the requirement, which is binding.
* Keep modules deep: Requirements should specify substantial behavior behind a compact interface,
  avoiding shallow 1-to-1 pass-through layers.
* Items under `## Open questions` or `## Out of scope` are **never implemented**.
* Keep files focused. Split a feature file once it holds more than about 25 requirements.

## Traceability tags (in src/ and test/) and linked issues

* Every test that verifies a requirement carries `@spec <ID>` in a comment, docstring, or test
  name, for example `// @spec AUTH-002` or `def test_lockout():  # @spec AUTH-002`.
  Several IDs: `@spec AUTH-001, AUTH-002`.
* The main implementing unit (function, class, handler, or module) carries a
  `@spec <ID>` comment. Shared infrastructure doesn't need tags.
* When a requirement or change is linked to an issue (e.g., `#42`), reference the issue in the
  requirement's `Notes:` section in `spec/` and alongside the `@spec <ID>` tag or docstring in
  `src/` and `test/` where appropriate (for example, `// @spec AUTH-002 (Issue #42)`).
* When follow-up work is tracked in an open issue, `TODO` comments referencing that open issue
  may be placed in `spec/`, `src/`, and `test/` (for example, `// TODO(#45): ...` or
  `<!-- TODO(#45): ... -->`). Once the referenced issue is fixed or closed, the `TODO` comment
  must be removed (it is okay to reference fixed or closed issues in normal comments, just not
  in `TODO` comments).
* `specdrive.py check` fails on untested requirements and on tags whose ID isn't in the spec
  (orphans).
