---
name: jetstream-new-repo
description: Create a new GitHub repo that starts on jetstream, the way .jetstream/docs/core/new-repo.md says - create and clone it, start main, run `jetstream new-repo` with uvx, set up and check it, and open its first pull request, then list the steps only an org owner can do. Use when the user says things like "new repo", "create a repo for ...", "start a new project", or "new-repo <name>". Not for an existing repo, which adopts jetstream (.jetstream/docs/core/adopting.md).
---

# Start a new repo

Follow `.jetstream/docs/core/new-repo.md`. It runs outside any repo, so read that doc from the jetstream repo the user is in, or from `https://github.com/cloudfeaster/jetstream/blob/main/src/jetstream/docs/core/new-repo.md`.

## 1. Ask for the inputs

Ask for everything in one go, and confirm the answers before creating anything, because a repo is hard to undo:

- **the org and the repo's name**;
- **a one-line description**;
- **what kind of repo it is**: core only (no Python code of its own), python (its own code is Python), or website. The website pack isn't ready yet: if they pick it, stop and say so;
- **private or public**: default to private. Public and private repos get the same files today.

## 2. Create the repo, and start main

`gh` must be logged in as an account that can create repos in the org (`gh auth status`).

```bash
gh repo create <org>/<repo> --private --description "<description>" --clone
cd <repo>
git commit --allow-empty -m "chore: start the repo"
git push -u origin main
git switch -c feat/start-on-jetstream
```

Use `--public` instead of `--private` if the user chose a public repo. Commits must be signed: if the commit can't be signed, stop and tell the user, and never use `--no-gpg-sign`. If the push to `main` is rejected, stop and show the user the error.

## 3. Write the first files

Use jetstream's latest release:

```bash
tag="$(gh release view --repo cloudfeaster/jetstream --json tagName --jq .tagName)"
uvx --from "git+https://github.com/cloudfeaster/jetstream@${tag}" jetstream new-repo --description "<description>"
```

Add `--pack python` for a python repo. If `new-repo` reports a problem, tell the user what it said.

## 4. Set up and check

```bash
source cfg4dev.sh
pre-commit run --all-files
```

A new repo should pass every check. If one fails, show the user what it reports: don't change jetstream's files to make it pass.

## 5. Open the first pull request

```bash
git add -A
git commit -m "feat: start on jetstream"
git push -u origin feat/start-on-jetstream
gh pr create --title "feat: start on jetstream" --body "The repo's first files, from \`jetstream new-repo\` (${tag})."
```

Wait for `jetstream lint` (`gh pr checks --watch`), and report the pull request's URL. Don't merge it: the user decides (see `jetstream-ship`).

## 6. List what an org owner does next

Once the pull request merges, an org owner does the last three steps of `.jetstream/docs/core/adopting.md`. List them for the user, with links to the docs:

1. set the repo's `jetstream` custom property to `true`;
1. set up its Dependabot alert sync (`dependabot-alerts.md`, "Adding a repo");
1. set up its jetstream updates (`jetstream-update.md`, "Adding a repo").
