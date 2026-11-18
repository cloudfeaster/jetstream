# jetstream

<p align="center">
  <img src="images/jetstream-hero.png" alt="jetstream logo: a cloud with orange jet streams" width="480">
</p>

jetstream standardizes the development workflow and toolchain for every Cloudfeaster repo.

Each jetstream release holds the approved dev toolchain (lint and security tools, all pinned), their configuration, `cfg4dev.sh`, VS Code settings, CI workflows, Claude Code plugins and shared conventions.

jetstream ships as a Python package, `cloudfeaster-jetstream`, that a repo adds as a dev dependency pinned to a release tag. A standard `uv sync` installs it, and every tool it pins, into the repo's `.venv`, and `jetstream sync` writes the configuration, so bumping that one pin moves the whole toolchain and its configuration together.

> **Status:** early development. The `jetstream` command and the packs aren't usable yet. The plan is [issue #1](https://github.com/cloudfeaster/jetstream/issues/1).

## The strict model

jetstream is deliberately strict:

- **Repos don't choose tool versions.** Only jetstream bumps a tool pin, and a repo picks up a whole release or none of it.
- **Repos don't edit jetstream's files or settings.** `jetstream sync` writes the files jetstream owns and its keys in `pyproject.toml`; every other key and file belongs to the repo.
- **Drift fails CI.** `jetstream check`, run as a pre-commit hook and in CI, fails when a repo differs from what its jetstream release would write.

## Packs

A repo selects packs in `[tool.jetstream] packs`:

| Pack | For |
|---|---|
| `core` | every repo: YAML, JSON, Markdown, shell, GitHub Actions, secrets, CI |
| `python` | Python packages: ruff, ty, bandit, licensecheck, pip-audit and more |
| `website` | Astro and Starlight sites on GitHub Pages |

## Supported platforms

Linux x86_64, Linux arm64 and macOS arm64. On any other platform, building jetstream stops with `*** jetstream: unsupported platform ...`.

## How jetstream is distributed

jetstream is published only as source, at its `vX.Y.Z` tags. That matters for licensing, so it's a rule, not just how things happen to work today:

1. **A jetstream wheel is only ever built on the machine that installs it.** `uv sync` fetches jetstream's source at the pinned tag and builds the wheel there. jetstream's build hook downloads each CLI binary pinned in `binaries.toml` from its publisher's own GitHub releases, checks its SHA-256, and puts it in that wheel.
1. **jetstream wheels are never published.** They aren't on PyPI or any other package index, they're never attached to a GitHub Release, and no container image has jetstream installed. CI doesn't keep them either: the generated `jetstream-lint.yaml` turns off uv's GitHub Actions cache, and jetstream's `release-assets` workflow fails if a release ever has a file attached.
1. **A wheel only installs the tools on that machine.** The binaries in it come from their publishers, and the wheel is used only to put them in the repo's `.venv/bin`. jetstream's Python tools, such as `shellcheck-py`, come from PyPI.

So jetstream installs its tools without distributing them, and under [the licensing policy](src/jetstream/docs/core/licensing.md) it can include development tools whatever their license, GPL-3.0 ShellCheck included. Each tool runs as a separate program on a repo's code and isn't linked into it, so it doesn't change that code's license. Changing any of this, for example publishing a built wheel, needs a licensing review first.

## Generic content only

jetstream is public and is installed by private, public and spun-out repos alike. It must never contain secrets, client names, internal hostnames or anything else specific to one project. The same secret-scanning and sensitive-value checks jetstream ships run on jetstream itself.

## Quick start

To install jetstream in a repo, pin a release in `pyproject.toml`:

```toml
[dependency-groups]
dev = ["cloudfeaster-jetstream[core]"]

[tool.uv.sources]
cloudfeaster-jetstream = { git = "https://github.com/cloudfeaster/jetstream", tag = "vX.Y.Z" }
```

Then set up the environment:

```bash
source cfg4dev.sh
```

uv is the only machine prerequisite (website repos also need Node).

## Working on jetstream

```bash
source cfg4dev.sh   # installs jetstream from this working tree into .venv
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
