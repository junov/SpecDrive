---
name: spec-submit
description: >-
  The final step of the SpecDrive process. Pushes committed changes to the upstream repository,
  closes associated issues completely fixed by the pushed commits, manages code reviews / pull
  requests with issue-closing annotations (e.g. 'Closes #123'), and comments 'Fixed in release <version>'
  on all fixed issues whenever release tags are pushed or merged.
---

# Spec-Submit

`spec-submit` is the final step in the SpecDrive delivery pipeline. Once changes have been synchronized, verified, and committed (`spec-sync` baseline commit or release version bump commit), `spec-submit` handles publishing those commits to the upstream repository, closing fixed issues, annotating code reviews (Pull Requests) for automated issue closure upon merge, and tagging issues with release notification comments.

---

## Workflow Steps

### 1. Identify Commits to Push & Fixed Issues
Inspect the unpushed commits:
```bash
git log @{u}..HEAD --oneline
```
(Or `git log origin/<current-branch>..HEAD` if an upstream tracking branch is not yet set).

For all unpushed commits:
1. Identify all associated issues mentioned in:
   - Commit messages and trailers (e.g. `Fixes #42`, `Closes #42`, `Issue #42`).
   - `spec/` requirement `Notes:` sections changed in the commits being pushed.
2. Confirm with the user which of these issues are **completely fixed** by the commits (as opposed to partially addressed or ongoing follow-ups).

---

### 2. Push Commits & Manage Code Reviews (PRs)

Determine whether the project or branch requires a code review (e.g. GitHub Pull Request) or uses direct push:

#### Option A: Code Review Required (Pull Request Workflow)
If contributing to a repository or branch that requires code review:
1. Push the branch to the remote:
   ```bash
   git push -u origin <branch-name>
   ```
2. Create or update the Pull Request / code review (e.g., via `gh pr create` or web interface).
3. **Annotate with Issue-Closing Keywords**:
   Ensure the code review description explicitly references the completely fixed issues using platform closing keywords (e.g. `Closes #123`, `Fixes #456`, `Resolves #789`).
   - *Why*: This ensures that the platform automatically closes the associated issues as soon as the pull request is approved and merged into the target branch.
   - For partially addressed issues, use non-closing references (e.g. `Addresses #123`, `Ref #123`).

#### Option B: Direct Push (No Code Review Required)
If pushing directly to the target branch (e.g. `main` or `master` where direct pushes are permitted):
1. Push the commits upstream:
   ```bash
   git push origin <branch-name>
   ```
2. **Close Completely Fixed Issues**:
   Immediately close the completely fixed issues via issue tracker CLI or API (e.g., GitHub CLI):
   ```bash
   gh issue close <issue-number> --comment "Fixed in commit <sha> via SpecDrive."
   ```

---

### 3. Handle Release Tags & Release Comments

Whenever a commit with new release tags is being pushed (e.g. tags created by release workflows like `publish`, such as `v1.0.10`):

1. **Push the Release Tag(s)**:
   ```bash
   git push origin <tag-name>
   # Or: git push origin --tags
   ```
2. **Find All Issues Fixed Since the Previous Release Tag**:
   Find the previous release tag:
   ```bash
   git describe --tags --abbrev=0 <tag-name>^
   ```
   Inspect the commit log between the previous tag and the new release tag:
   ```bash
   git log <prev-tag>..<tag-name> --oneline
   ```
   Collect all issues that were closed or fixed across that commit range.
3. **Post Release Comments**:
   For every issue that was fixed since the previous release tag, post a comment to the issue:
   ```bash
   gh issue comment <issue-number> --body "Fixed in release <version>"
   ```
   *(e.g., `gh issue comment 42 --body "Fixed in release v1.0.10"`)*.

---

### 4. Summary & Confirmation
Present a concise submission summary to the user:
- Pushed commits and target branch/remote.
- Code review / Pull Request link (if created) with closing annotations noted.
- Closed issues (if direct push).
- Release tags pushed and issues commented with `"Fixed in release <version>"`.
