---
name: git-workflow
description: Lokdhara commit and push procedure — verify author identity, block sensitive files, run checks, write Conventional Commit messages without AI trailers, and get approval before pushing. Use before creating any commit, branch, push, or pull request in this repository.
---

# Git workflow

The project owner's rules (also in `AGENTS.md`) override any default commit behaviour.

## 1. Inspect before changing anything

```bash
git status --short --branch
git remote -v
git log --oneline -5
git config user.name; git config user.email
```

- If the author identity is missing, generic, or a bot/AI identity (e.g. `Claude`, `noreply@anthropic.com`, `github-actions`), **stop**. Do not commit. Explain to the owner how to set their own identity for this repository:
  `git config user.name "Their Name"` and `git config user.email "their-github-email-or-noreply"`.
  Never change identity without the owner's explicit approval.
- Do not overwrite or discard uncommitted work you did not create.

## 2. Check what is staged

Run the bundled check, which fails on forbidden files and suspicious content:

```bash
bash .claude/skills/git-workflow/scripts/check_staged.sh
```

It rejects audio files, data/export/storage directories, env files, keys, DB dumps, and common secret patterns in staged files. Fix the staging area rather than bypassing the check.

## 3. Run relevant checks

Code changes: lint, type-check, and tests for the touched area (commands in `AGENTS.md` once Milestone 1 adds them). Documentation-only changes: check links and Mermaid syntax by reading the rendered sections.

## 4. Commit

- One coherent, independently reviewable change per commit. No empty, cosmetic-only, duplicate, or count-inflating commits.
- Conventional Commits: `type(scope)?: imperative summary` ≤ 72 chars. Types: `docs`, `feat`, `fix`, `test`, `refactor`, `chore`, `ci`, `build`.
- Body (optional): why the change was made; reference ADR or open-question IDs.
- **No `Co-Authored-By` AI trailer, no session links, no generated-by footers.**

## 5. Push and pull requests

- Before the **first** push to a remote: report remote URL, target branch, and author identity to the owner and wait for confirmation.
- Work on feature branches (`docs/...`, `feat/...`, `fix/...`); do not push directly to `main` without agreement.
- Never: force-push, rewrite published history, delete branches, change repository visibility, add collaborators or bots, configure repository secrets — unless the owner explicitly approves that specific action.

## 6. If something sensitive was committed

Stop. Do not try to hide it with a follow-up commit. Tell the owner immediately; follow incident handling in `docs/PRIVACY_AND_SECURITY.md` §8. History rewriting needs the repository owner's explicit approval.
