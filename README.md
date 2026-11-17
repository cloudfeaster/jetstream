# jetstream

<p align="center">
  <img src="images/jetstream-hero.png" alt="jetstream logo: a cloud with orange jet streams" width="480">
</p>

jetstream defines how every Cloudfeaster repo's development environment works, and packages it.

It's a Python package, `cloudfeaster-jetstream`, released as git tags. A release holds the approved dev toolchain (lint and security tools, all pinned), their configuration, `cfg4dev.sh`, VS Code settings, CI workflows, Claude Code plugins and shared conventions. A repo installs one jetstream release into its `.venv`, and bumping that one pin moves the whole toolchain and its configuration together.

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
| `core` | every repo: YAML, JSON, Markdown, shell, GitHub Actions, secrets, DCO, CI |
| `python` | Python packages: ruff, ty, bandit, licensecheck, pip-audit and more |
| `website` | Astro and Starlight sites on GitHub Pages |

## Supported platforms

Linux x86_64, Linux arm64 and macOS arm64. On any other platform, building jetstream stops with `*** jetstream: unsupported platform ...`.

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
