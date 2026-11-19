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

The pack also installs coverage, and core's `unit-tests` hook then runs the tests under it: the hook fails if coverage is below 80% (branch coverage, of every `*.py` file except `tests/`, so a file no test imports counts as 0%). `.coverage` is left behind, so `coverage html` shows what's missed.

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
