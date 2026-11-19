"""The TOML half of the python pack's prune checks, run by its ``run-prune-*.sh`` scripts.

Each prune check finds entries in a repo's ``pyproject.toml`` that no longer
change what uv locks, so they can be removed. The scripts run ``uv lock`` on a
copy of the project, once per entry; this module reads and rewrites the copy's
``pyproject.toml`` and ``uv.lock`` for them. It runs no subprocess, so ruff's
and bandit's subprocess rules have nothing to flag.

Usage, each printing one item per line::

    python -m jetstream.prune constraints PYPROJECT
    python -m jetstream.prune invert-constraint PYPROJECT INDEX
    python -m jetstream.prune exclude-newer-packages PYPROJECT
    python -m jetstream.prune remove-exclude-newer-package PYPROJECT PACKAGE
    python -m jetstream.prune locked-version UV_LOCK PACKAGE
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import Any, Final

import tomlkit

# A constraint the patch-vuln skill writes: a floor, `"foo>=1.2.3"`.
FLOOR: Final[re.Pattern[str]] = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*>=\s*([^\s,;]+)\s*$")

EXIT_OK: Final[int] = 0
EXIT_ERROR: Final[int] = 2


class PruneError(Exception):
    """A problem with the entries to check, reported in one line."""


def normalize(name: str) -> str:
    """Return a package name as uv.lock writes it (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def uv_table(document: dict[str, Any]) -> dict[str, Any]:
    """Return ``[tool.uv]``, or an empty table."""
    return document.get("tool", {}).get("uv", {})


def constraints(pyproject: Path) -> list[str]:
    """Return ``[tool.uv] constraint-dependencies``, in order."""
    return [str(spec) for spec in uv_table(tomllib.loads(pyproject.read_text())).get("constraint-dependencies", [])]


def invert(spec: str) -> str:
    """Return the requirement that allows only what the floor ``spec`` rules out: ``foo>=1.2.3`` gives ``foo<1.2.3``."""
    match: re.Match[str] | None = FLOOR.match(spec)
    if match is None:
        msg: str = f"constraint '{spec}' isn't a floor such as 'foo>=1.2.3', so it can't be checked"
        raise PruneError(msg)
    return f"{match[1]}<{match[2]}"


def invert_constraint(pyproject: Path, index: int) -> str:
    """Replace constraint ``index`` in ``pyproject`` with its inverse, keeping comments, and return the inverse."""
    document: tomlkit.TOMLDocument = tomlkit.parse(pyproject.read_text())
    tool: Any = document["tool"]
    specs: Any = tool["uv"]["constraint-dependencies"]
    inverse: str = invert(str(specs[index]))
    specs[index] = inverse
    pyproject.write_text(tomlkit.dumps(document))
    return inverse


def exclude_newer_packages(pyproject: Path) -> list[str]:
    """Return the packages in ``[tool.uv] exclude-newer-package``."""
    return list(uv_table(tomllib.loads(pyproject.read_text())).get("exclude-newer-package", {}))


def remove_exclude_newer_package(pyproject: Path, package: str) -> None:
    """Remove ``package``'s override from ``pyproject``, keeping everything else as it was."""
    document: tomlkit.TOMLDocument = tomlkit.parse(pyproject.read_text())
    tool: Any = document["tool"]
    overrides: Any = tool["uv"]["exclude-newer-package"]
    del overrides[package]
    pyproject.write_text(tomlkit.dumps(document))


def locked_versions(uv_lock: Path, package: str) -> list[str]:
    """Return every version of ``package`` in ``uv_lock``, sorted (a lock can hold more than one, for different markers)."""
    packages: list[dict[str, Any]] = tomllib.loads(uv_lock.read_text()).get("package", [])
    return sorted(str(entry["version"]) for entry in packages if normalize(entry["name"]) == normalize(package) and "version" in entry)


def run(argv: list[str]) -> list[str]:
    """Run one command and return the lines it prints."""
    match argv:
        case ["constraints", path]:
            return constraints(Path(path))
        case ["invert-constraint", path, index]:
            return [invert_constraint(Path(path), int(index))]
        case ["exclude-newer-packages", path]:
            return exclude_newer_packages(Path(path))
        case ["remove-exclude-newer-package", path, package]:
            remove_exclude_newer_package(Path(path), package)
            return []
        case ["locked-version", path, package]:
            return [" ".join(locked_versions(Path(path), package))]
        case _:
            msg: str = "usage: python -m jetstream.prune constraints | invert-constraint | exclude-newer-packages | remove-exclude-newer-package | locked-version (see the module's docstring)"
            raise PruneError(msg)


def main(argv: list[str] | None = None) -> int:
    """Run ``python -m jetstream.prune`` and return its exit status."""
    try:
        lines: list[str] = run(sys.argv[1:] if argv is None else argv)
    except PruneError as e:
        sys.stderr.write(f"*** jetstream prune: {e}\n")
        return EXIT_ERROR
    for line in lines:
        sys.stdout.write(f"{line}\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
