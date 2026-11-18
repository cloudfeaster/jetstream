<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Development workflow

How a change gets from an idea to the default branch (`main`) in a Cloudfeaster repo.

## The rules

An org ruleset applies the same rules to every repo's default branch, and no one can bypass them, admins included:

- changes reach `main` only through a pull request, and a direct `git push` to it is rejected;
- the `jetstream lint` check (the `jetstream-lint.yaml` workflow) must pass, on a branch that's up to date with `main`;
- every commit must be signed (GPG, SSH or S/MIME) and verified by GitHub;
- force-pushes to `main` and deleting it are blocked.

No approving review is required, so a pull request can merge as soon as `jetstream lint` passes. Locally, the `no-commit-to-branch` pre-commit hook stops a commit on `main` before the push would be rejected.

Commit messages are [Conventional Commits](https://www.conventionalcommits.org/) (`feat: ...`, `fix: ...`, `docs: ...`).

## Signing commits

Set this up before your first push. With GPG:

```bash
gpg --full-generate-key                     # create a key, if you don't have one
gpg --list-secret-keys --keyid-format=long  # find the key ID
git config --global user.signingkey <key-id>
git config --global commit.gpgsign true
gpg --armor --export <key-id>               # add this to GitHub: Settings → SSH and GPG keys
```

To sign with an existing SSH key instead (`gpg.format = ssh`), see [GitHub's docs](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits).

## Steps

In Claude Code, `/jetstream-new-feature` does steps 1 to 3 and `/jetstream-ship` does steps 2 to 5, stopping for your go-ahead before it merges.

1. **Branch** from an up-to-date `main`, with a descriptive name such as `feat/add-export` or `fix/date-parsing`:

    ```bash
    git switch main && git pull
    git switch -c feat/add-export
    ```

1. **Commit**. The pre-commit hooks run first (see [dev-environment.md](dev-environment.md)); if one fails, fix what it reports and commit again.

1. **Push, and open a draft pull request** right away. `jetstream lint` runs on pull requests, so an early draft gets CI on every push:

    ```bash
    git push -u origin feat/add-export
    gh pr create --draft --fill
    ```

1. **Mark it ready and merge** once `jetstream lint` passes. Squash-merge, so `main` has one commit per pull request:

    ```bash
    gh pr ready
    gh pr merge --squash --delete-branch
    ```

    If `main` moved on in the meantime, GitHub asks for the branch to be updated first (`gh pr update-branch`), and the check runs again.

1. **Clean up** your local branch:

    ```bash
    git switch main && git pull
    git branch -D feat/add-export
    ```

    `-D` is needed because a squash merge makes a new commit on `main`, so git doesn't see the branch as merged.

## Taking a jetstream release

Dependabot opens a pull request when jetstream releases, changing the tag in `pyproject.toml` and the lock in `uv.lock`. That's all Dependabot can change, so when a release also changes files jetstream owns, `jetstream check` fails on the pull request, naming each file:

```text
*** jetstream: .github/workflows/jetstream-lint.yaml differs from what jetstream writes
*** jetstream: run `jetstream sync` and commit what it changes
```

That's deliberate: a repo takes a whole release or none of it, so the new tools can't merge with the old configuration. A release that changes no owned files passes as it is, so just merge it. Otherwise, add `jetstream sync`'s changes to the pull request:

1. **Check out the pull request** and set up the environment, which runs `uv sync` (installing the new release) and then `jetstream sync`:

    ```bash
    deactivate 2>/dev/null   # if another repo's .venv is active, so it can't shadow this one's jetstream
    gh pr checkout <number>
    source cfg4dev.sh
    ```

    `jetstream sync: wrote ...` lists the files it changed, and `jetstream --version` shows the new release.

1. **Commit and push** the changes, including any new files the release adds:

    ```bash
    git add -A
    git commit -m "chore: jetstream sync for vX.Y.Z"
    git push
    ```

1. **Review the sync commit**: its diff is what the release actually changes in this repo. Merge once `jetstream lint` passes, then clean up as above.

Once you've pushed to its branch, Dependabot stops updating the pull request. If `main` moves on before you merge, update the branch (`gh pr update-branch`), and run `jetstream check` again.
