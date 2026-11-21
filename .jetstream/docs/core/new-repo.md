<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Starting a new repo

A new repo starts on jetstream with `jetstream new-repo`, which writes the repo's first files. An existing repo adopts it instead ([adopting.md](adopting.md)). The org has to be set up for jetstream first, once ([org-setup.md](org-setup.md)).

In Claude Code, `/jetstream-new-repo` does steps 1 to 5, then lists step 6.

1. **Create the repo and clone it.** Make it private unless it's meant to be public:

    ```bash
    gh repo create <org>/<repo> --private --description "<what the repo is>" --clone
    cd <repo>
    ```

1. **Start `main`** with an empty commit, so the default branch exists before any work. The org's rulesets then apply to it:

    ```bash
    git commit --allow-empty -m "chore: start the repo"
    git push -u origin main
    git switch -c feat/start-on-jetstream
    ```

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

1. **An org owner finishes the setup**, once it merges, with the last three steps of [adopting.md](adopting.md): the repo's `jetstream` custom property, its Dependabot alert sync, and its jetstream updates.
