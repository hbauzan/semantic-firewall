# GIT AND VERSION CONTROL WORKFLOW (Gitstuff)

Follow these rules for committing code, running hooks, and maintaining version safety.

---

## 1. GIT METADATA BLOCK

Upon successful completion of a logical task, always append a dedicated Git Metadata block at the absolute end of your response using the following format:

```yaml
Branch Name: <type>/<short-descriptive-name>  # e.g., feat/backend-auth-jwt or fix/ui-navbar-responsive
Commit Message: <type>(<scope>): <short description in present tense> # e.g., feat(auth): implement JWT validation middleware
```

---

## 2. PRE-COMMIT HOOK CONVENTIONS

To ensure code quality and formatting are consistent before any commit is finalized, the repository leverages Husky and lint-staged.

### 2.1. Guardrail Setup
- **lint-staged**: Runs formatting tools (such as Prettier: `prettier --ignore-unknown --write`) on staged files only, to keep commits fast.
- **Verification Scripts**: Runs full typecheck and test scripts (e.g. `npm run typecheck && npm run test` or the `pnpm`/`uv` equivalent) inside the hook.
- **Smoke Testing**: Always run `npx lint-staged` locally to verify correctness before pushing or resolving a task.

---

## 3. AGENT GIT GUARDRAILS (SAFETY RULES)

To prevent accidental data loss, branch corruption, or unauthorized code publication, agents must be constrained by safety hooks.

### 3.1. Prohibited Git Commands
The following commands are strictly blocked for agents:
- `git push` (all variants including force pushes)
- `git reset --hard` (use soft resets or git restore on specific files if necessary)
- `git clean -f` / `git clean -fd`
- `git branch -D`
- `git checkout .` / `git restore .` (reverting the entire working directory)

### 3.2. Claude Code Integration
When running in Claude Code or compatible terminals, a `PreToolUse` matcher hook must be registered to run a blocker script (e.g., `.claude/hooks/block-dangerous-git.sh`) that intercepts and aborts these commands before execution.
