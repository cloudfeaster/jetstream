<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Python

The python pack is for a repo whose own code is Python. It adds these hooks to core's ([dev-environment.md](../core/dev-environment.md)), and they check every tracked `*.py` file, tests included unless the table says otherwise:

| Hook | What it checks |
|---|---|
| `ruff` | `ruff check` (every rule, with a few left out) and `ruff format --check`, with jetstream's `[tool.ruff]` keys |
| `ty` | types, with ty's default rules, using the repo's `.venv` for its dependencies |
| `bandit` | security issues, with jetstream's `[tool.bandit]` keys; it leaves out `tests/`, which ruff's `S` rules (bandit's, ported) still check |
| `deptry` | the dependencies in `pyproject.toml` against what the code imports: every import is declared, every dependency is used, and no dev dependency is imported; deptry's defaults leave out `tests/` |
| `pyscn` | a health score for complexity, dead code, clones, coupling and cohesion, which must be at least 90; `pyscn analyze --html .` shows the details |
| `pip-audit` | no known vulnerabilities in any package in `uv.lock`, jetstream's tools included, like `trivy` but with PyPI's advisories; it runs at every commit, and every night in `jetstream-nightly-sca.yaml` |
| `licensecheck` | the licenses of the product dependencies (`[project] dependencies`, and theirs) are ones [licensing.md](../core/licensing.md) allows, with jetstream's `[tool.licensecheck]` keys; dev dependencies, jetstream among them, are left out |

The pack also installs coverage, and core's `unit-tests` hook then runs the tests under it: the hook fails if coverage is below 80% (branch coverage, of every `*.py` file except `tests/`, so a file no test imports counts as 0%). `.coverage` is left behind, so `coverage html` shows what's missed.

The pack's `jetstream-python-ci.yaml` workflow builds the sdist and wheel (`uv build`) on every pull request and push to `main`, to prove they still build. It keeps nothing: publishing a wheel needs a licensing review first ([licensing.md](../core/licensing.md)).

None of the hooks changes a file. To fix what ruff reports:

```bash
ruff check --fix
ruff format
```

## ruff's configuration

jetstream sets ruff's keys in `pyproject.toml`: `line-length` (256: break lines where it reads well), `select = ["ALL"]`, the `ignore` list, the pylint and mccabe limits, and the format options. The repo can:

- leave its own files out with `[tool.ruff] exclude`;
- add rules with ruff's `extend-*` keys, such as `[tool.ruff.lint] extend-per-file-ignores`.

It can't change a key jetstream sets, including removing a rule from `ignore`: jetstream owns each list as a whole. A rule that's wrong for every repo is a change to jetstream.

A `# noqa: <code>` comment turns off one finding on one line. Name the rule, and say why if it isn't obvious. bandit doesn't read `noqa`: its comment is `# nosec <code>`, such as `# nosec B310`. bandit reads every word after `nosec` as a rule, so give the reason in a comment of its own.

## pip-audit's exceptions

pip-audit's exceptions work as trivy's do (see [dev-environment.md](../core/dev-environment.md#vulnerabilities)), in the same format: a finding in jetstream's tools is excepted in jetstream's `.jetstream/pip-audit-ignore`, in a release, and a finding in the repo's own dependencies in its `.pip-audit-ignore`. An exception stops applying on its `exp:` date:

```text
CVE-2026-12345 exp:2026-12-01  # fixed in foo 1.2.3 (2026-11-26), inside the 7-day cooldown
```

As with trivy, the nightly `jetstream-prune-pip-audit-ignore.yaml` fails, naming the exception, once pip-audit no longer finds what an exception in `.pip-audit-ignore` is for (`run-prune-pip-audit-ignore.sh`).

Use the CVE ID, or the GHSA ID if there's no CVE: pip-audit matches an exception against a finding's aliases, so the same ID works in `.trivyignore`. To force a transitive dependency up to a fixed version, add a `[tool.uv] constraint-dependencies` entry rather than a dependency. In Claude Code, `/jetstream-patch-vuln <ID>` works through a finding.

## Pruning `[tool.uv]`

Two `[tool.uv]` lists in `pyproject.toml` hold entries that are only needed for a while, and never expire. Each has a nightly workflow that fails, naming the entry, once it no longer changes what uv locks, so it can be removed:

| Workflow | Checks | Redundant when |
|---|---|---|
| `jetstream-prune-constraints.yaml` | `constraint-dependencies`, each a floor such as `"foo>=1.2.3",  # CVE-2026-12345` | the dependencies allow nothing older: a copy of the project with `foo<1.2.3` instead can't lock |
| `jetstream-prune-exclude-newer-package.yaml` | `exclude-newer-package` overrides, each letting a package past the 7-day cooldown | the version it let in has cleared the cooldown: a copy of the project without it locks the same version |

They lock a copy of `pyproject.toml` and `uv.lock`, never the repo's own. To run one yourself, run `run-prune-constraints.sh` or `run-prune-exclude-newer-package.sh`.

## licensecheck's policy

jetstream sets `[tool.licensecheck]`: `only_licenses` (MIT, Apache and BSD) and `ignore_packages`, the exceptions. licensecheck can't tell a transitive dependency from a direct one, so an MPL-2.0 transitive dependency, which licensing.md allows, is added to `ignore_packages` by name. Like every license exception, that's a change to jetstream, not to the repo.

## deptry's configuration

jetstream sets no deptry keys, so the repo sets `[tool.deptry]` itself when its layout needs it, for example `known_first_party = ["<package>"]` when its code is under `src/`. See [deptry's docs](https://deptry.com/usage/).

## Type annotations

Annotate every variable assigned with `=`, in tests too, and make module constants `Final`:

```python
from typing import Final

TIMEOUT: Final[float] = 10.0


def total(prices: list[float], tax_rate: float) -> float:
    subtotal: float = sum(prices)
    return subtotal * (1 + tax_rate)
```
