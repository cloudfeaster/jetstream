# Starting a new repo

A new repo starts on jetstream with `jetstream new-repo`, which writes the repo's first files. An existing repo adopts it instead ([adopting.md](adopting.md)). The org has to be set up for jetstream first, once ([org-setup.md](org-setup.md)).

In Claude Code, `/jetstream-new-repo` does steps 1 to 6, then lists step 7.

1. **Create the repo and clone it.** Make it private unless it's meant to be public. `gh repo create` turns a repo's wiki on unless told not to, and Cloudfeaster repos don't have one:

    ```bash
    gh repo create <org>/<repo> --private --disable-wiki --description "<what the repo is>" --clone
    cd <repo>
    ```

1. **Start `main`** with an empty commit, so the default branch exists before any work. The org's rulesets then apply to it. A clone of an empty repo names its branch after git's `init.defaultBranch`, so name it `main` before pushing:

    ```bash
    git commit --allow-empty -m "chore: start the repo"
    git branch -M main
    git push -u origin main
    git switch -c feat/start-on-jetstream
    ```

1. **An org owner sets the repo up for jetstream**, before its first pull request merges:

    1. **Mark it as using jetstream:** set its `jetstream` custom property to `true` ([org-setup.md](org-setup.md)), so the org's `default branch: jetstream lint` ruleset requires `jetstream lint` from the first pull request on:

        ```bash
        gh api -X PATCH orgs/<org>/properties/values --input - <<< '{"repository_names": ["<repo>"], "properties": [{"property_name": "jetstream", "value": "true"}]}'
        ```

        A new repo can be marked straight away, unlike one adopting jetstream ([adopting.md](adopting.md)): its first pull request adds `jetstream-lint.yaml`, and a pull request runs the workflows in its own changes, so the required check runs on it.

    1. **Set up its Dependabot alert sync:** [dependabot-alerts.md](dependabot-alerts.md), "Adding a repo", up to testing it.
    1. **Set up its jetstream updates:** [jetstream-update.md](jetstream-update.md), "Adding a repo", up to testing it.

    A repo marked as using jetstream is expected to have all three, so do them together.

1. **Write the first files.** The repo has no `.venv` yet, so run jetstream's latest release with `uvx`:

    ```bash
    uvx --from "git+https://github.com/cloudfeaster/jetstream@<vX.Y.Z>" jetstream new-repo --description "<what the repo is>"
    ```

    Add `--pack python` for a repo whose own code is Python. `new-repo` pins the release it ran from and writes the files the repo owns from then on: `pyproject.toml`, `README.md`, `CONTRIBUTING.md`, `CLAUDE.md` and `.trivyignore`. With the python pack, it also writes `.pip-audit-ignore`, an empty package, and `pyproject.toml`'s `[build-system]` (hatchling), `[project.urls]` and wheel target. Then it runs `jetstream sync`, which writes the files jetstream owns ([dev-environment.md](dev-environment.md)).

1. **Set up and check:**

    ```bash
    source cfg4dev.sh
    git add -A
    pre-commit run --all-files
    ```

    `cfg4dev.sh` runs `uv sync`, which writes `uv.lock`. `--all-files` checks only the files git tracks, so stage the new ones first, or most hooks check nothing.

1. **Commit, open a pull request, and merge** once `jetstream lint` passes ([dev-workflow.md](dev-workflow.md)):

    ```bash
    git add -A
    git commit -m "feat: start on jetstream"
    git push -u origin feat/start-on-jetstream
    gh pr create --fill
    ```

1. **Test the alert sync and the updates** once it merges, by running each workflow by hand on `main`, as their "Adding a repo" sections say.
