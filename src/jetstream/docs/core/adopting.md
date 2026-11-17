# Adopting jetstream

How to bring an existing repo onto jetstream. A new repo starts on it.

1. **Branch** from `main` ([dev-workflow.md](dev-workflow.md)).

1. **Set up `pyproject.toml`.** A repo that isn't a Python package still gets one, because uv builds its dev environment. The minimum, for the core pack:

    ```toml
    [project]
    name = "<repo name>"
    version = "0.0.0"
    description = "<what the repo is>"
    requires-python = "==3.13.*"
    dependencies = []

    [dependency-groups]
    dev = [
        "cloudfeaster-jetstream[core]",
    ]

    [tool.uv]
    package = false  # not a Python package: uv only manages the dev environment

    [tool.uv.sources]
    cloudfeaster-jetstream = { git = "https://github.com/cloudfeaster/jetstream", tag = "<vX.Y.Z>" }

    [tool.jetstream]
    packs = ["core"]
    ```

    Until jetstream's first release, pin a commit instead: `rev = "<commit SHA>"`. The extras on `cloudfeaster-jetstream` are the repo's packs (`[core,python]`, ...), and `[tool.jetstream] packs` lists the same ones.

1. **Install and sync:**

    ```bash
    uv sync
    uv run jetstream sync
    source cfg4dev.sh
    ```

    `jetstream sync` writes the files jetstream owns, its block in `.gitignore` and its keys in `pyproject.toml` ([dev-environment.md](dev-environment.md)). Where the repo already had one of those files, the repo's version is replaced, so look at `git diff` for anything worth keeping: a setting moves into `pyproject.toml` or the repo's own setup in `cfg4dev.local.sh`, and a check becomes a test.

1. **Remove what jetstream replaces**: the repo's old lint workflows and configs, and its old setup script.

1. **Make the hooks pass:**

    ```bash
    pre-commit run --all-files
    ```

    Fix what they find. Each finding is a real one, but a genuine false positive goes in `.gitleaksignore` or `.trivyignore`.

1. **Point the docs at jetstream's.** `CONTRIBUTING.md` links to `.jetstream/docs/`, and `CLAUDE.md` imports the docs Claude should follow:

    ```text
    @.jetstream/docs/core/behavioral-guidelines.md
    @.jetstream/docs/core/dev-workflow.md
    ```

1. **Commit, open a pull request, and merge** once `jetstream lint` passes. The org ruleset requires `jetstream lint`, so a repo can't merge any pull request until it has adopted jetstream.
