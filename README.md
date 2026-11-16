# jetstream

Shared development infrastructure for Cloudfeaster repos: pre-commit hooks, reusable CI workflows, Claude Code plugins and a copier template. See [cloudfeaster/jetstream#1](https://github.com/cloudfeaster/jetstream/issues/1) for the plan.

## pre-commit hooks

Each hook installs its own pinned tool on first use, so a repo only needs [pre-commit](https://pre-commit.com), plus Node for the two markdownlint hooks. Add jetstream to the repo's `.pre-commit-config.yaml`, pinned to a full commit SHA:

```yaml
repos:
  - repo: https://github.com/cloudfeaster/jetstream
    rev: <full commit SHA>  # vX.Y.Z
    hooks:
      - id: yamllint
      - id: shellcheck
      - id: markdownlint
      - id: mado-config-up-to-date  # before mado, so mado reads the current mado.toml
      - id: mado
      - id: zizmor
```

| Hook | Tool | Config it reads from the repo |
|---|---|---|
| `yamllint` | [yamllint](https://github.com/adrienverge/yamllint), run with `--strict` | `.yamllint` |
| `shellcheck` | [ShellCheck](https://github.com/koalaman/shellcheck) | `.shellcheckrc`, if present |
| `markdownlint` | [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2) | `.markdownlint.json` |
| `mado-config-up-to-date` | Generates `mado.toml` from `.markdownlint.json` | `.markdownlint.json` |
| `mado` | [mado](https://github.com/akiomik/mado), a faster Markdown linter | `mado.toml` (generated) |
| `zizmor` | [zizmor](https://github.com/zizmorcore/zizmor) GitHub Actions security checks, offline | `zizmor.yml` or `.github/zizmor.yml`, if present |

Without `.yamllint` or `.markdownlint.json`, those tools use their own defaults, which include an 80-character line limit. This repo's `.yamllint` and `.markdownlint.json` are a good starting point.

### Keeping mado and markdownlint in step

`.markdownlint.json` is the only Markdown config to edit. `mado-config-up-to-date` generates `mado.toml` from it, using both tools' config schemas: markdownlint's from its npm package, and mado's from [`hooks/core/mado-<version>.schema.json`](hooks/core). For every rule mado has, `mado.toml` turns it on if markdownlint has it and `.markdownlint.json` turns it on, and sets each option to the value in `.markdownlint.json` or else markdownlint's default, because the two tools' defaults differ. If the generated file differs from the repo's `mado.toml`, the hook writes it and fails, so the change gets reviewed and committed. It also fails, naming the rule, if `.markdownlint.json` asks for something mado can't express, such as markdownlint's default `MD029` style `one_or_ordered`, or an option mado doesn't have.

`.markdownlint.json` must use rule IDs (`MD013`, not `line-length`) and no `extends`.

### Where each tool's version is pinned

| Tools | Pinned in | Bumped by |
|---|---|---|
| yamllint, ShellCheck, zizmor | [`pyproject.toml`](pyproject.toml), one extra per hook | Dependabot (pip) |
| markdownlint-cli2 | [`package.json`](package.json) | Dependabot (npm) |
| mado | [`hooks/core/install-mado.sh`](hooks/core/install-mado.sh), with a SHA-256 per platform | the nightly `bin/check-tool-versions.sh` fails, then `bin/update-mado.sh <version>` |

mado isn't on PyPI (the `mado` package there is an unrelated project), so `install-mado.sh` downloads its GitHub release into `~/.cache/jetstream/mado/<version>/` and checks the pinned SHA-256 first. `bin/update-mado.sh <version>` sets the version and every SHA-256 from the release's `.sha256` files, and replaces the vendored schema. Run pre-commit afterwards to regenerate `mado.toml`.

### npm 11

pre-commit 4.7.0 can't install Node hooks with npm 11, which comes with Node 24: npm fails with `EALLOWGIT`. npm 10 and npm 12 both work. With Node 24, run `npm install -g npm@12`.

### Trying changes

To try uncommitted hook changes against another repo, run this from that repo:

```bash
pre-commit try-repo /path/to/jetstream --all-files
```
