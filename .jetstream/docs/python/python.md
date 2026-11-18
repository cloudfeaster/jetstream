<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Python

The python pack is for a repo whose own code is Python. It adds these hooks to core's ([dev-environment.md](../core/dev-environment.md)), and they check every tracked `*.py` file, tests included:

| Hook | What it checks |
|---|---|
| `ruff` | `ruff check` (every rule, with a few left out) and `ruff format --check`, with jetstream's `[tool.ruff]` keys |
| `ty` | types, with ty's default rules, using the repo's `.venv` for its dependencies |

Neither hook changes a file. To fix what they report:

```bash
ruff check --fix
ruff format
```

## ruff's configuration

jetstream sets ruff's keys in `pyproject.toml`: `line-length` (256: break lines where it reads well), `select = ["ALL"]`, the `ignore` list, the pylint and mccabe limits, and the format options. The repo can:

- leave its own files out with `[tool.ruff] exclude`;
- add rules with ruff's `extend-*` keys, such as `[tool.ruff.lint] extend-per-file-ignores`.

It can't change a key jetstream sets, including removing a rule from `ignore`: jetstream owns each list as a whole. A rule that's wrong for every repo is a change to jetstream.

A `# noqa: <code>` comment turns off one finding on one line. Name the rule, and say why if it isn't obvious.

## Type annotations

Annotate every variable assigned with `=`, in tests too, and make module constants `Final`:

```python
from typing import Final

TIMEOUT: Final[float] = 10.0


def total(prices: list[float], tax_rate: float) -> float:
    subtotal: float = sum(prices)
    return subtotal * (1 + tax_rate)
```
