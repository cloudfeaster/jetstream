---
name: jetstream-new-feature
description: Start a branch the way .jetstream/docs/core/dev-workflow.md says (steps 1 and 3) - branch from an up-to-date main with a descriptive name such as feat/add-export, push it, and open a draft pull request straight away so jetstream lint runs on every push. Use when the user says things like "start a new feature", "new branch for ...", "new-feature <name>", or is beginning work that will land through a pull request. Pairs with jetstream-ship, which finishes the branch.
model: haiku
---

# Start a branch

The first half of `.jetstream/docs/core/dev-workflow.md`: a branch and a draft pull request exist before the work does, so `jetstream lint` checks every push, not just the last one.

## 1. Pick the branch name

Use the name the user gave. Otherwise propose one in the `<type>/<short-description>` form, where `<type>` is a Conventional Commits type (`feat/add-export`, `fix/date-parsing`, `docs/...`), and check it with the user.

## 2. Branch from an up-to-date main

```bash
git status
git branch --show-current
```

If you're on a branch other than `main`, stop and ask the user: don't branch off a branch without being told to. Uncommitted changes go with you onto the new branch, so mention them if there are any.

```bash
git switch main && git pull
git switch -c <branch-name>
```

## 3. Push, and open a draft pull request

GitHub won't open a pull request for a branch with no commits ahead of `main`, so start with an empty commit. The squash merge absorbs it.

```bash
git commit --allow-empty -m "chore: start <short description of the planned work>"
git push -u origin <branch-name>
gh pr create --draft --title "<conventional-commit title>" --body "<one line on the planned work>"
```

- Commits must be signed (dev-workflow.md "Signing commits"). If the commit fails because it can't be signed, stop and tell the user; never commit with `--no-gpg-sign`.
- If the pre-commit hooks fail, fix what they report and commit again; never use `--no-verify`.
- If the title or description isn't clear from the conversation, ask for a one-line description: there's no diff to summarize yet.

Report the pull request's URL.
