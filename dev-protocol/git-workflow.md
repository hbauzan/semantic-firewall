# GIT AND VERSION CONTROL WORKFLOW (Gitstuff)

Follow these rules for committing code, running hooks, and maintaining version safety.

---

## 1. GIT METADATA BLOCK

Upon successful completion of a logical task, always append a dedicated Git Metadata block at the absolute end of your response using the following format:

```yaml
Branch Name: <type>/<short-descriptive-name>  # e.g., feat/provider-fallback or fix/client-timeout-retry
Commit Message: <type>(<scope>): <short description in present tense> # e.g., feat(llm): add local-to-remote provider fallback
```

---

## 2. PRE-COMMIT HOOK CONVENTIONS

To keep code quality and formatting consistent before any commit is finalized, use the Python **`pre-commit`** framework (configured via a `.pre-commit-config.yaml` at the workspace root). This replaces Node-centric tooling (Husky / lint-staged) for Python projects.

A ready-to-use base config ships with this protocol at [`templates/.pre-commit-config.yaml`](./templates/.pre-commit-config.yaml) — copy it to the workspace root and pin the `rev:` tags.

### 2.1. Recommended Hook Setup
Conventions (swappable per app, but stay consistent within a repo):
- **Format + Lint**: `ruff format` and `ruff check --fix` on staged files (fast, autofixing).
- **Type Check**: a static type check (`mypy` or `pyright`) in CI or as a manual-stage hook (type checking the whole project can be slow for a per-commit hook).
- **Secret Scan**: a secret-detection hook (e.g. `detect-secrets` / `gitleaks`) to enforce the "no keys in git" rule from [README.md](./README.md) §3.2.
- **Hygiene**: trailing-whitespace, end-of-file-fixer, and a check that `.env` is never staged.

### 2.2. Installation & Smoke Testing
- Install the git hook once per clone: `uv run pre-commit install`.
- Always smoke-test locally before pushing or resolving a task: `uv run pre-commit run --all-files`.
- For a JS/TS frontend that exists alongside (see [README.md](./README.md) §3.3), wire its own formatter via that ecosystem's tooling; do not impose Python hooks on JS files or vice versa.

---

## 3. GIT DELIVERY & AUTOMATION POLICY

The agent **owns the full git lifecycle and executes it automatically** — branch, stage, commit, push, and merge to the base branch — gated by a single mandatory human checkpoint. Push and merge are **allowed**; they are not blocked.

### 3.1. The Approval Gate (mandatory)
- The agent may **freely** create branches, stage files, and commit **locally** at any point while working.
- The agent must **NOT `git push` and must NOT merge to the base branch** until the user has verified the change and given an **explicit go-ahead** (e.g. "ok", "dale", "andá", "mergealo"). 
- Reporting "ready to test" and then **waiting** is mandatory. Silence, a thumbs-up on something unrelated, or the absence of objection is **not** approval.

### 3.2. Delivery Sequence (run only after approval)
Default sequence once the user approves:
1. `git checkout -b <type>/<short-name>` — if not already on a dedicated task branch.
2. Stage **only files relevant to the task**. Leave unrelated untracked/modified files alone; if scope is unclear, ask (see §3.3).
3. `git commit` using the metadata format from §1, ending with the `Co-Authored-By` trailer.
4. `git push -u origin <branch>`.
5. `git checkout <base>` → `git merge --no-ff <branch>` → `git push origin <base>`. (`<base>` is usually `main`.)
6. *(Optional, ask first)* delete the merged branch locally and on the remote.

> Alternative: if the repo works through pull requests, substitute steps 4–5 with `gh pr create` + merge. Default to the direct merge above unless the user or repo conventions say otherwise.

### 3.3. Stop-and-Ask Conditions ("when it gets complicated")
**Pause and ask the user** before continuing if any of these arise during delivery:
- Merge conflicts, or the base branch has diverged / moved since branching.
- A pre-commit hook, type check, test, or CI check **fails**.
- The base branch is **protected**, or the push is rejected.
- A **force-push** (`--force` / `--force-with-lease`) would be required.
- Commit **scope is ambiguous** (unrelated changes staged, or unrelated untracked files present that might belong in the commit).
- The remote, credentials, or target branch are **not what was expected**.

### 3.4. Destructive Commands (always require explicit confirmation)
These are **not** part of the normal flow and risk irreversible data loss. Never run them autonomously — propose the command and get an explicit "yes" first:
- `git reset --hard` (prefer a soft reset or `git restore <file>`).
- `git clean -f` / `git clean -fd`.
- `git branch -D`.
- `git checkout .` / `git restore .` (reverting the entire working directory).
- Any history rewrite on an already-pushed branch (`rebase`, `commit --amend` after push, force-push).

### 3.5. Claude Code Integration
Optionally register a `PreToolUse` matcher hook (e.g., `.claude/hooks/block-dangerous-git.sh`) that intercepts **only the §3.4 destructive commands**. `git push` and `git merge` must **not** be blocked — they are governed by the approval gate (§3.1), not by a hook.
