# jetstream

Shared development infrastructure for Cloudfeaster repos: pre-commit hooks, reusable CI workflows, Claude Code plugins and a copier template. See [cloudfeaster/jetstream#1](https://github.com/cloudfeaster/jetstream/issues/1) for the plan.

## pre-commit hooks

Each hook installs its own pinned tool on first use, so a repo only needs [pre-commit](https://pre-commit.com). Add jetstream to the repo's `.pre-commit-config.yaml`, pinned to a full commit SHA:

```yaml
repos:
  - repo: https://github.com/cloudfeaster/jetstream
    rev: <full commit SHA>  # vX.Y.Z
    hooks:
      - id: yamllint
      - id: shellcheck
      - id: mado
      - id: zizmor
```

| Hook | Tool | Config it reads from the repo |
|---|---|---|
| `yamllint` | [yamllint](https://github.com/adrienverge/yamllint), run with `--strict` | `.yamllint` |
| `shellcheck` | [ShellCheck](https://github.com/koalaman/shellcheck) | `.shellcheckrc`, if present |
| `mado` | [mado](https://github.com/akiomik/mado) Markdown linter | `mado.toml` |
| `zizmor` | [zizmor](https://github.com/zizmorcore/zizmor) GitHub Actions security checks, offline | `zizmor.yml` or `.github/zizmor.yml`, if present |

Without `.yamllint` or `mado.toml`, those tools use their own defaults, which include an 80-character line limit. This repo's `.yamllint` and `mado.toml` are a good starting point.

Python tools are installed by pre-commit from PyPI at the versions pinned in [`pyproject.toml`](pyproject.toml), one extra per hook, which is where Dependabot can see and bump them. mado isn't on PyPI (the `mado` package there is an unrelated project), so [`hooks/core/mado.sh`](hooks/core/mado.sh) downloads its GitHub release into `~/.cache/jetstream/mado/<version>/` and checks a pinned SHA-256 before running it.

To try uncommitted hook changes against another repo, run this from that repo:

```bash
pre-commit try-repo /path/to/jetstream --all-files
```
