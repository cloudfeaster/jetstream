---
name: jetstream-ship
description: Finish a branch the way .jetstream/docs/core/dev-workflow.md says (steps 2, 4 and 5) - commit what's pending, push, mark the pull request ready, wait for jetstream lint, then stop for the user's go-ahead before squash-merging and cleaning up the branch. Use when the user says things like "ship this", "ship it", or "merge when green". Pairs with jetstream-new-feature, which starts the branch.
---

# Ship a branch

The second half of `.jetstream/docs/core/dev-workflow.md`: takes a branch through to `main`, and always stops before the merge, the one step that's hard to undo.

**Packs add to this skill.** For each `*.md` file next to this one (such as the public pack's `coderabbit.md`), read it before going on: it says what its pack adds before the merge.

## 1. Check the branch and its pull request

```bash
git branch --show-current   # must not be main
gh pr view --json number,isDraft,url
```

If the branch has no pull request yet, push it and open one (not a draft: this is the finish):

```bash
git push -u origin <branch-name>
gh pr create --title "<conventional-commit title>" --body "<what and why>"
```

## 2. Commit and push

```bash
git status
git diff
```

Commit what's pending with a Conventional Commits message (`feat: ...`, `fix: ...`, `docs: ...`) that says why, not just what. Then `git push`. If nothing is pending, go on to step 3.

- Commits must be signed. If a commit can't be signed, stop and tell the user; never use `--no-gpg-sign`.
- If the pre-commit hooks fail, fix what they report and commit again; never use `--no-verify`.

## 3. Mark it ready

```bash
gh pr ready <number>   # only if it's a draft
```

## 4. Wait for jetstream lint

`main` only takes a pull request that passes `jetstream lint` on a branch that's up to date with it. If `main` has moved on, update the branch first, which runs the check again:

```bash
gh pr update-branch <number>   # only if it's behind main
gh pr checks <number> --watch
```

- **A check fails:** stop. Say which check failed and link the run. Don't merge.
- **The checks pass:** first do what any pack's file next to this one adds (such as working through CodeRabbit's review), then tell the user, and **stop**. Don't merge until they say so.

## 5. Merge (only after the user's go-ahead)

```bash
gh pr merge <number> --squash --delete-branch
```

Squash, so `main` has one commit per pull request.

## 6. Clean up the local branch

```bash
git switch main && git pull
git branch -D <branch-name>
```

`-D` is needed because a squash merge makes a new commit on `main`, so git doesn't see the branch as merged.
