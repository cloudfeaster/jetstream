<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Starting a new repo

A new repo starts on jetstream with `jetstream new-repo`, which writes the repo's first files. An existing repo adopts it instead ([adopting.md](adopting.md)). The org has to be set up for jetstream first, once ([org-setup.md](org-setup.md)).

In Claude Code, `/jetstream-new-repo` does steps 1 to 6, then lists step 7.

1. **Create the repo and clone it.** Make it private unless it's meant to be public:

    ```bash
    gh repo create <org>/<repo> --private --description "<what the repo is>" --clone
    cd <repo>
    ```

1. **Start `main`** with an empty commit, so the default branch exists before any work. The org's rulesets then apply to it. A clone of an empty repo names its branch after git's `init.defaultBranch`, so name it `main` before pushing:

    ```bash
    git commit --allow-empty -m "chore: start the repo"
    git branch -M main
    git push -u origin main
    git switch -c feat/start-on-jetstream
    ```

1. **Mark the repo as using jetstream.** An org owner sets its `jetstream` custom property to `true` ([org-setup.md](org-setup.md)), so the org's `default branch: jetstream lint` ruleset requires `jetstream lint` from the first pull request on:

    ```bash
    gh api -X PATCH orgs/<org>/properties/values --input - <<< '{"repository_names": ["<repo>"], "properties": [{"property_name": "jetstream", "value": "true"}]}'
    ```

    A new repo can be marked straight away, unlike one adopting jetstream ([adopting.md](adopting.md)): its first pull request adds `jetstream-lint.yaml`, and a pull request runs the workflows in its own changes, so the required check runs on it.

1. **Write the first files.** The repo has no `.venv` yet, so run jetstream's latest release with `uvx`:

    ```bash
    uvx --from "git+https://github.com/cloudfeaster/jetstream@<vX.Y.Z>" jetstream new-repo --description "<what the repo is>"
    ```

    Add `--pack python` for a repo whose own code is Python. `new-repo` pins the release it ran from and writes the files the repo owns from then on: `pyproject.toml`, `README.md`, `CONTRIBUTING.md`, `CLAUDE.md` and `.trivyignore`. With the python pack, it also writes `.pip-audit-ignore`, an empty package, and `pyproject.toml`'s `[build-system]` (hatchling), `[project.urls]` and wheel target. Then it runs `jetstream sync`, which writes the files jetstream owns ([dev-environment.md](dev-environment.md)).

1. **Set up and check:**

    ```bash
    source cfg4dev.sh
    pre-commit run --all-files
    ```

    `cfg4dev.sh` runs `uv sync`, which writes `uv.lock`.

1. **Commit, open a pull request, and merge** once `jetstream lint` passes ([dev-workflow.md](dev-workflow.md)):

    ```bash
    git add -A
    git commit -m "feat: start on jetstream"
    git push -u origin feat/start-on-jetstream
    gh pr create --fill
    ```

1. **An org owner finishes the setup**, once it merges, with the last two steps of [adopting.md](adopting.md): the repo's Dependabot alert sync, and its jetstream updates.
