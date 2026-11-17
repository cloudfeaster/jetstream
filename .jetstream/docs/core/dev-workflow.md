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
