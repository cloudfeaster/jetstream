<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Python

The python pack is for a repo whose own code is Python. It adds these hooks to core's ([dev-environment.md](../core/dev-environment.md)), and they check every tracked `*.py` file, tests included unless the table says otherwise:

| Hook | What it checks |
|---|---|
| `ruff` | `ruff check` (every rule, with a few left out) and `ruff format --check`, with jetstream's `[tool.ruff]` keys |
| `ty` | types, with ty's default rules, using the repo's `.venv` for its dependencies |
| `bandit` | security issues, with jetstream's `[tool.bandit]` keys; it leaves out every path with `tests` in it, which ruff's `S` rules (bandit's, ported) still check |
| `deptry` | the dependencies in `pyproject.toml` against what the code imports: every import is declared, every dependency is used, and no dev dependency is imported; deptry's defaults leave out a top-level `tests/` (see [Tests](#tests) for tests beside the code) |
| `pyscn` | a health score for complexity, dead code, clones, coupling and cohesion, which must be at least 90; `pyscn analyze --html .` shows the details |
| `pip-audit` | no known vulnerabilities in any package in `uv.lock`, jetstream's tools included, like `trivy` but with PyPI's advisories; it runs at every commit, and every night in `jetstream-nightly-sca.yaml` |
| `python-licenses` | the licenses of the product dependencies (`[project] dependencies`, and theirs) are ones [licensing.md](../core/licensing.md) allows, by SPDX ID (see [Product licenses](#product-licenses)); dev dependencies, jetstream among them, are left out |

The pack also installs coverage, and core's `unit-tests` hook then runs the tests under it: the hook fails if coverage is below 80% (branch coverage, of every `*.py` file except those in a `tests/` folder, so a file no test imports counts as 0%). `.coverage` is left behind, so `coverage html` shows what's missed.

`jetstream lint` also builds the sdist and wheel (`uv build`) on every pull request and push to `main`, to prove they still build, so a pull request that breaks the build can't merge. It keeps nothing: publishing a wheel needs a licensing review first ([licensing.md](../core/licensing.md)).

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

## Product licenses

The `python-licenses` hook (`run-python-licenses.sh`) reads each product dependency's license from the package installed in `.venv`, as SPDX IDs: its `License-Expression`, or failing that its `License` if that's made of licenses licensing.md allows, or failing that its license classifiers if each names one license (`MIT License`, but not `BSD License`, which doesn't say which BSD). It compares IDs, not words, so `FSL-1.1-MIT` and `BSD-4-Clause` fail, and it knows a direct dependency from a transitive one, so MPL-2.0 passes only as a transitive one.

A package whose metadata doesn't say clearly fails until someone reads its license file and records the license in jetstream's `python-licenses.toml`, with the version reviewed. Like every license exception, that's a change to jetstream, not to the repo. A recorded package fails again if a later version says clearly that it has another license.

## deptry's configuration

jetstream sets no deptry keys, so the repo sets `[tool.deptry]` itself when its layout needs it, for example `known_first_party = ["<package>"]` when its code is under `src/`. See [deptry's docs](https://deptry.com/usage/).

## Dependencies

- **Product dependencies** go in `[project] dependencies`, each pinned exactly (`"foo==1.2.3"`), with a comment saying what it's for. Dependabot then proposes every upgrade as a pull request, and `uv.lock` changes only when one merges.
- **Development tools** go in `[dependency-groups] dev`, next to jetstream itself (`cloudfeaster-jetstream[core,python]`), and are pinned exactly too. A tool jetstream already installs isn't added again: it's already in `.venv/bin`.
- **A transitive dependency** that must be newer than what's locked, for a vulnerability fix, gets a `[tool.uv] constraint-dependencies` floor, not a dependency of its own (see [pip-audit's exceptions](#pip-audits-exceptions) and [Pruning `[tool.uv]`](#pruning-tooluv)).
- `[tool.uv] exclude-newer` keeps every new release out for 7 days, so a compromised one is usually pulled before it's locked. To let one package in sooner, add an `exclude-newer-package` override, which its prune workflow removes once it's redundant.

deptry checks that the code imports every product dependency and no dev dependency.

## Tests

Tests are pytest functions, in either layout:

- **a top-level `tests/`**: `tests/test_<module>.py` tests `<package>/<module>.py`;
- **beside the code**: `<package>/tests/test_<module>.py` tests `<package>/<module>.py`, and imports it relatively (`from .. import <module>`). Each `tests/` folder needs an `__init__.py`.

Coverage and bandit leave out both. deptry's defaults only leave out a top-level `tests/`, so a repo with tests beside its code adds:

```toml
[tool.deptry]
extend_exclude = [".*/tests/"]
```

Conventions:

- **Every test has a docstring** saying what it checks (ruff's `D103`). A fixture or helper's docstring starts with an imperative ("Return ...").
- **Use `@pytest.mark.parametrize`** for cases of the same test, not a loop over a list: each case gets its own ID, and can fail and be run on its own.
- **Shared fixtures** go in a `conftest.py`, at the root or in the `tests/` folder that uses them.
- **Build test files from data**, not long string literals: write a `dict` with `yaml.dump()` or `json.dumps()`, so a case can change one value. A test of a parse error is the exception.
- **A test that's slow or needs the network**, such as one that runs a real subprocess, is marked `@pytest.mark.integration` ([dev-environment.md](../core/dev-environment.md#the-checks)), or `pytestmark = pytest.mark.integration` for a whole module. The `unit-tests` hook leaves them out, so they don't count towards coverage.

## Validating config with JSON Schema

When code reads a YAML or JSON config file, validate it against a JSON Schema with the `jsonschema` package, rather than checking keys one at a time with `.get()`. A schema with `"additionalProperties": false` catches a misspelled key, which would otherwise be silently ignored.

- Each schema is a `.json` file in a `jsonschemas/` folder beside the module that uses it, formatted as `jq` formats it ([json.md](../core/json.md)).
- A `jsonschemas.py` module loads each one into a variable of the same name, one line per schema, so ty can see every name. Don't call it `jsonschema.py`: it would shadow the `jsonschema` package in a module that imports both.
- The code catches `jsonschema.ValidationError` and raises a `ValueError` that names the file.
- If a schema uses `format` (such as `"format": "regex"`), pass `format_checker=jsonschema.FormatChecker()`. Without it, `format` isn't checked.

```python
import json
from pathlib import Path
from typing import Any, Final


def _load(name: str) -> dict[str, Any]:
    """Return the schema in jsonschemas/<name>.json."""
    return json.loads((Path(__file__).parent / "jsonschemas" / f"{name}.json").read_text())


config: Final[dict[str, Any]] = _load("config")
```

```python
import jsonschema

from . import jsonschemas


def validate_config(data: object, path: str) -> None:
    """Raise ValueError if the config read from path doesn't match its schema."""
    try:
        jsonschema.validate(data, jsonschemas.config, format_checker=jsonschema.FormatChecker())
    except jsonschema.ValidationError as exc:
        msg: str = f"invalid config in {path}: {exc.message}"
        raise ValueError(msg) from exc
```

## Installing from more than one index

Most repos only use PyPI. One that also needs another package index (for a prebuilt wheel, say) should know that uv doesn't treat indexes the way pip does:

- uv looks at every `--index` (or `[[tool.uv.index]]`) **before** the default index, and by default it stops at the first index that has the package at all, even if it only has an sdist there. Put the index that should win on `--index`, and keep `--default-index` for the fallback. The old names, `--extra-index-url` and `--index-url`, read the other way round.
- Add `--only-binary <package>` (or `--no-build`) to an install that should get a wheel. Otherwise a mistake in which index wins can quietly build the package from source, which takes minutes, rather than failing in seconds.
- `exclude-newer` applies to `uv pip install` too. An index that publishes no upload times (a plain list of files, not a PEP 700 index) has nothing uv can check against the cutoff, so nothing from it resolves, whatever the cutoff. The only way round it is `--no-config`, for a package pinned and reviewed some other way.
- To find which CI step got slower, get each step's real times with `gh api repos/<owner>/<repo>/actions/jobs/<job-id> --jq '.steps[] | [.name, .started_at, .completed_at]'`, compare a slow run with a fast one, and read the slow step's whole log. A warm cache can hide a wrong resolution.

## Type annotations

Annotate every variable assigned with `=`, in tests too, and make module constants `Final`:

```python
from typing import Final

TIMEOUT: Final[float] = 10.0


def total(prices: list[float], tax_rate: float) -> float:
    subtotal: float = sum(prices)
    return subtotal * (1 + tax_rate)
```
