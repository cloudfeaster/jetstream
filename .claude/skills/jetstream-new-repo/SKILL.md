---
name: jetstream-new-repo
description: Create a new GitHub repo that starts on jetstream, the way .jetstream/docs/core/new-repo.md says - create and clone it, start main, set it up for jetstream, run `jetstream new-repo` with uvx, set up and check it, and open its first pull request, then list the steps only an org owner can do. Use when the user says things like "new repo", "create a repo for ...", "start a new project", or "new-repo <name>". Not for an existing repo, which adopts jetstream (.jetstream/docs/core/adopting.md).
---

# Start a new repo

Follow `.jetstream/docs/core/new-repo.md`. It runs outside any repo, so read that doc from the jetstream repo the user is in, or from `https://github.com/cloudfeaster/jetstream/blob/main/src/jetstream/docs/core/new-repo.md`.

## 1. Ask for the inputs

Ask for everything in one go, and confirm the answers before creating anything, because a repo is hard to undo:

- **the org and the repo's name**;
- **a one-line description**;
- **what kind of repo it is**: core only (no Python code of its own), python (its own code is Python), or website. The website pack isn't ready yet: if they pick it, stop and say so;
- **private or public**: default to private. A public repo adds the public pack once it's started (step 7).

Then check that `gh` is logged in as an org owner (`gh api orgs/<org>/memberships/$(gh api user --jq .login) --jq .role` says `admin`). If it isn't, say that an owner must do step 3, before the first pull request merges, and carry on.

## 2. Create the repo, and start main

`gh` must be logged in as an account that can create repos in the org (`gh auth status`).

```bash
gh repo create <org>/<repo> --private --disable-wiki --description "<description>" --clone
cd <repo>
git commit --allow-empty -m "chore: start the repo"
git branch -M main  # a clone of an empty repo names its branch after git's init.defaultBranch
git push -u origin main
git switch -c feat/start-on-jetstream
```

Use `--public` instead of `--private` if the user chose a public repo. Keep `--disable-wiki`: the org's repos have no wiki. Commits must be signed: if the commit can't be signed, stop and tell the user, and never use `--no-gpg-sign`. If the push to `main` is rejected, stop and show the user the error.

## 3. Set the repo up for jetstream

`.jetstream/docs/core/new-repo.md` step 3, as an org owner. A repo marked as using jetstream is expected to have all three of these, so do them together.

1. **Mark it as using jetstream:** set its `jetstream` custom property to `true`, so `jetstream lint` is required from the first pull request on. The first pull request adds `jetstream-lint.yaml`, so the check runs on it:

    ```bash
    gh api -X PATCH orgs/<org>/properties/values --input - <<< '{"repository_names": ["<repo>"], "properties": [{"property_name": "jetstream", "value": "true"}]}'
    ```

1. **The Dependabot alert sync** (`dependabot-alerts.md`, "Adding a repo") **and the jetstream updates** (`jetstream-update.md`, "Adding a repo") each need the user to add the repo to an App's installation and generate the App a key, in the browser. Ask them to do both, and to tell you where each `.pem` file was downloaded. Then create each environment and store its key with the commands in those sections, and delete the downloads.

If `gh` isn't an owner's, a call fails, or the user would rather do it later, don't stop: tell them an owner must do all three before the first pull request merges.

## 4. Write the first files

Use jetstream's latest release:

```bash
tag="$(gh release view --repo cloudfeaster/jetstream --json tagName --jq .tagName)"
uvx --from "git+https://github.com/cloudfeaster/jetstream@${tag}" jetstream new-repo --description "<description>"
```

Add `--pack python` for a python repo. If `new-repo` reports a problem, tell the user what it said.

## 5. Set up and check

```bash
source cfg4dev.sh
pre-commit run --all-files
```

A new repo should pass every check. If one fails, show the user what it reports: don't change jetstream's files to make it pass.

## 6. Open the first pull request

```bash
git add -A
git commit -m "feat: start on jetstream"
git push -u origin feat/start-on-jetstream
gh pr create --title "feat: start on jetstream" --body "The repo's first files, from \`jetstream new-repo\` (${tag})."
```

Wait for `jetstream lint` (`gh pr checks --watch`), and report the pull request's URL. Don't merge it: the user decides (see `jetstream-ship`).

## 7. List what's left

List these for the user, with links to the docs:

1. anything in step 3 that wasn't done, for an org owner to do before the first pull request merges;
1. once it merges, test the alert sync and the updates by running each workflow by hand on `main` (their "Adding a repo" sections);
1. for a public repo, once it merges, add the public pack on a new branch, as `.jetstream/docs/public/coderabbit.md` says ("Adding the pack"): `jetstream new-repo` doesn't take it.
