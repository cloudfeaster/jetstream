# Development workflow

How a change gets from an idea to the default branch (`main`) in a Cloudfeaster repo.

## The rules

Org rulesets apply the same rules to the default branch of every repo that uses jetstream, and no one can bypass them, admins included ([org-setup.md](org-setup.md)):

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

When jetstream releases, the `jetstream-update.yaml` workflow opens a pull request, `build(deps): update jetstream from vA to vB`, by the next morning. It changes the tag in `pyproject.toml`, the lock in `uv.lock`, and every file `jetstream sync` changes, in one commit ([jetstream-update.md](jetstream-update.md)). A repo takes a whole release or none of it, so the new tools can't merge with the old configuration.

1. **Review the pull request.** Its diff is what the release actually changes in this repo.
1. **Merge it** once `jetstream lint` passes, as in step 4 above. Locally, `source cfg4dev.sh` then installs the new release.

Don't push to `jetstream/update`: the workflow makes its commit again, and resets the branch, each time a newer release comes out or `main` moves on. To fix something the release breaks in the repo, merge the update first, then fix it in a pull request of its own, or fix it in jetstream.

To take a release before the workflow next runs, run it by hand: `gh workflow run jetstream-update.yaml`.
