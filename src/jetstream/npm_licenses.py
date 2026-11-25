"""The website pack's npm license check, run by its ``run-npm-licenses.sh``.

A site's product dependencies are the packages in ``package-lock.json`` that
aren't dev dependencies: what its ``dependencies`` bring in, which can end up
in the built site. Each must have a license licensing.md allows in a product:
MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC or 0BSD, or MPL-2.0 for a
transitive dependency only (decision 24). ``devDependencies``, Astro and the
rest of the build toolchain, are development tools, so they aren't checked.

npm writes each package's license into the lockfile, as an SPDX expression
such as ``MIT`` or ``(MIT OR Apache-2.0)``, so nothing needs installing.

The repo's own packages, the root and its workspaces, aren't checked. A
``file:`` dependency on any other folder, in the repo or not, is a package like
any other: npm writes a link to the folder, and its license on an entry for it.

Usage, printing each package that fails (exit 1), or why the lockfile can't be
checked (exit 2)::

    python -m jetstream.npm_licenses PACKAGE_LOCK
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Final

# The licenses licensing.md allows in a product dependency. An exception is a
# change to jetstream, not to a repo (licensing.md "Exceptions").
ALLOWED: Final[frozenset[str]] = frozenset({"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD"})
ALLOWED_TRANSITIVE: Final[frozenset[str]] = ALLOWED | {"MPL-2.0"}

WORD: Final[re.Pattern[str]] = re.compile(r"\(|\)|[^\s()]+")


def allows(expression: str, allowed: frozenset[str]) -> bool:
    """Return whether SPDX ``expression`` can be met with ``allowed`` licenses: any side of an OR, every side of an AND; a malformed one can't."""
    words: list[str] = WORD.findall(expression)
    position: int = 0

    def either() -> bool:
        nonlocal position
        result: bool = both()
        while position < len(words) and words[position] == "OR":
            position += 1
            result = both() or result
        return result

    def both() -> bool:
        nonlocal position
        result: bool = one()
        while position < len(words) and words[position] == "AND":
            position += 1
            result = one() and result
        return result

    def one() -> bool:
        nonlocal position
        if position >= len(words) or words[position] in {")", "AND", "OR", "WITH"}:
            raise ValueError(expression)  # a missing license
        word: str = words[position]
        position += 1
        if word == "(":
            result: bool = either()
            if position >= len(words) or words[position] != ")":
                raise ValueError(expression)  # an unclosed parenthesis
            position += 1
            return result
        if position < len(words) and words[position] == "WITH":  # a license with an exception: not one licensing.md lists
            if position + 1 >= len(words) or words[position + 1] in {"(", ")", "AND", "OR", "WITH"}:
                raise ValueError(expression)  # WITH and no exception
            position += 2
            return False
        return word in allowed

    try:
        result: bool = either()
    except ValueError:
        return False
    return result and position == len(words)


def installed_path(packages: dict[str, dict[str, Any]], owner: str, name: str) -> str | None:
    """Return where in ``packages`` the dependency ``name`` of the package at ``owner`` is installed, found as Node finds it: in the nearest node_modules/ at or above ``owner``."""
    folder: str = owner
    while True:
        candidate: str = f"{folder}/node_modules/{name}" if folder else f"node_modules/{name}"
        if candidate in packages:
            return candidate
        if not folder:
            return None
        folder = folder.rpartition("/")[0]


def is_own(path: str, workspaces: list[str]) -> bool:
    """Return whether the package at ``path`` is the repo's own: the root, or one that matches its ``workspaces`` patterns, where the last match wins and ``!`` excludes."""
    if not path:
        return True
    parts: tuple[str, ...] = PurePosixPath(path).parts
    if "node_modules" in parts or ".." in parts:
        return False
    matches: list[str] = [pattern for pattern in workspaces if PurePosixPath(path).full_match(pattern.removeprefix("!"))]
    return bool(matches) and not matches[-1].startswith("!")


def failures(lockfile: dict[str, Any]) -> list[str]:
    """Return a line for each product dependency in ``lockfile`` whose license isn't allowed."""
    packages: dict[str, dict[str, Any]] = lockfile.get("packages", {})
    workspaces: list[str] | dict[str, list[str]] = packages.get("", {}).get("workspaces", [])
    patterns: list[str] = workspaces.get("packages", []) if isinstance(workspaces, dict) else workspaces
    own: dict[str, dict[str, Any]] = {path: package for path, package in packages.items() if is_own(path, patterns)}
    links: dict[str, str] = {path: package["resolved"] for path, package in packages.items() if package.get("link")}
    installed: set[str] = {where for path, package in own.items() for key in ("dependencies", "optionalDependencies") for name in package.get(key, {}) if (where := installed_path(packages, path, name)) is not None}
    direct: set[str] = {links.get(path, path) for path in installed}
    found: list[str] = []
    for path, package in packages.items():
        # what a link points at has an entry of its own
        if path in own or path in links or package.get("dev"):
            continue
        license_: object = package.get("license")
        allowed: frozenset[str] = ALLOWED if path in direct else ALLOWED_TRANSITIVE
        if not isinstance(license_, str) or not allows(license_, allowed):
            kind: str = "a direct" if path in direct else "a transitive"
            found.append(f"{path} {package.get('version', '')}: {license_ or 'no license'} isn't allowed in {kind} product dependency")
    return found


def main(argv: list[str]) -> int:
    """Check the lockfile named in ``argv``, printing each failure; return 1 if there are any, and 2 if it can't be checked."""
    lockfile: dict[str, Any] = json.loads(Path(argv[0]).read_text())
    if not isinstance(lockfile.get("packages"), dict):
        sys.stderr.write(f"{argv[0]} has no packages table, so it's from npm 6 or older: run npm install with npm 7 or later to rewrite it\n")
        return 2
    found: list[str] = failures(lockfile)
    for line in found:
        sys.stdout.write(f"{line}\n")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
