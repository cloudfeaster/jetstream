<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Development environment

Every Cloudfeaster repo is set up the same way, by [jetstream](https://github.com/cloudfeaster/jetstream). The only thing you install yourself is [uv](https://docs.astral.sh/uv/) (and Node, for a website).

## Setting up

```bash
source cfg4dev.sh
```

`cfg4dev.sh`:

1. updates uv (`uv self update`);
1. runs `uv sync`, which builds `.venv` and installs the repo's dependencies, jetstream, and every tool jetstream pins, including the downloaded binaries, into `.venv/bin`;
1. activates `.venv`, so the tools are on `PATH`;
1. runs `jetstream sync`, and `uv sync` again if that changed `pyproject.toml`;
1. runs `pre-commit install`, for the `pre-commit` git hook;
1. sources `cfg4dev.local.sh`, if the repo has one, for the repo's own setup.

Run it again whenever you like; it only changes what's out of date. In VS Code, every new terminal runs it for you (`.vscode/terminal-init.sh`). CI doesn't use it: the `jetstream-lint.yaml` workflow runs `uv sync --locked` itself.

## jetstream sync and jetstream check

`jetstream sync` writes the files jetstream owns into the repo, from the packs in `pyproject.toml`'s `[tool.jetstream] packs` and the jetstream release the repo pins. `jetstream check` fails, naming each file, if the repo differs from what `sync` would write. It runs as a pre-commit hook and in CI, so a change to a file jetstream owns can't merge.

To change one of those files, change it in jetstream, then bump the repo's jetstream pin and run `jetstream sync`.

## The four kinds of files

| Kind | Examples | Who changes it |
|---|---|---|
| **Owned by jetstream** | `cfg4dev.sh`, `.pre-commit-config.yaml`, the tool configs (`mado.toml`, `.yamllint`, `.shellcheckrc`, `.trivy.yaml`, `.jsonlintignore`), `.vscode/`'s `settings.json`, `terminal-init.sh` and `.gitignore`, `.claude/settings.json`, `.claude/skills/jetstream-*/`, `.github/dependabot.yml`, `.github/workflows/jetstream-*.yaml`, `.jetstream/docs/` and `.jetstream/trivyignore` | jetstream; `sync` writes them, `check` enforces them |
| **Owned by the repo** | `cfg4dev.local.sh`, `.trivyignore`, `.gitleaksignore`, `CONTRIBUTING.md`, `CLAUDE.md`, and the repo's own workflows | the repo |
| **A jetstream block in a repo's file** | `.gitignore`, between `# >>> jetstream` and `# <<< jetstream` | jetstream inside the block, the repo outside it |
| **Both set values** | `pyproject.toml` | jetstream sets certain keys, such as `requires-python` and `[tool.uv] exclude-newer`, and the repo owns every other key, including keys it adds to jetstream's tables |

jetstream owns `.github/workflows/jetstream-*.yaml`, `.claude/skills/jetstream-*/` and `.jetstream/docs/` outright: `sync` deletes any file there that the release doesn't write. The repo's own Claude Code skills go in `.claude/skills/` under any other name.

## The checks

The pre-commit hooks, which CI also runs (`pre-commit run --all-files`), all call tools in `.venv/bin`:

| Hook | What it checks |
|---|---|
| `jetstream-check` | the files jetstream owns are what it writes |
| `no-commit-to-branch` | you aren't committing on `main` |
| `lockfile` | `uv.lock` matches `pyproject.toml` |
| `yamllint`, `json-lint`, `mado`, `shellcheck` | YAML, JSON ([json.md](json.md)), Markdown ([markdown.md](markdown.md)) and shell scripts |
| `sqlfluff` | SQL (`*.sql`, and `*.sql.j2` Jinja templates), with jetstream's `[tool.sqlfluff]` keys; the repo sets `[tool.sqlfluff.core] dialect`, and the values its templates need in `[tool.sqlfluff.templater.jinja.context]` |
| `zizmor` | GitHub Actions workflows ([github-actions.md](github-actions.md)) |
| `check-svg` | diagrams match their D2 sources ([diagrams.md](diagrams.md)) |
| `gitleaks` | no secrets in the git history; a false positive goes in `.gitleaksignore` |
| `trivy` | no known vulnerabilities in the lockfiles (see [Vulnerabilities](#vulnerabilities)) |
| `unit-tests` | the repo's tests pass (pytest, leaving out those marked `integration`); with the python pack, under coverage too (see its `python.md`) |

To run them all, as CI does:

```bash
pre-commit run --all-files
```

A repo can't add hooks. It adds a check by adding a test, which the `unit-tests` hook runs.

A slow test, such as one that needs the network, is marked `@pytest.mark.integration`. No hook runs those: the `jetstream-lint.yaml` workflow runs them after the hooks, with `run-integration-tests.sh`, which you can also run yourself.

## Vulnerabilities

The `trivy` hook scans the lockfiles at every commit, and the `jetstream-nightly-sca.yaml` workflow scans them every night, so a new advisory fails without anyone pushing. GitHub emails a failed run to whoever last changed the workflow's schedule, usually whoever committed the `jetstream sync` that wrote it.

A finding is fixed by whoever owns the vulnerable package. `uv tree --invert --package <name>` shows why it's there.

- **Only jetstream's tools need it** (every path leads to `cloudfeaster-jetstream`): jetstream fixes it, or adds a temporary exception to `.jetstream/trivyignore`, in a release. The repo doesn't ignore it, so its scans keep failing until it takes that release. Close any Dependabot pull request that bumps one of jetstream's dependencies.
- **The repo's own dependencies need it**: the repo upgrades or pins them, or, if no fixed version can be used yet, adds a temporary exception to `.trivyignore`.

An exception expires 7 days out, so it's reviewed again: `CVE-2026-12345 exp:2026-12-01  # why, and when to look again`.

In Claude Code, `/jetstream-patch-vuln <ID>` works through a finding this way.
