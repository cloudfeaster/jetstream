"""The python pack's license check of a repo's product dependencies, run by its ``run-python-licenses.sh``.

A repo's product dependencies are its ``[project] dependencies`` and theirs:
what ``uv export --no-dev`` lists. Each must have a license licensing.md allows
in a product, with MPL-2.0 for a transitive dependency only. Dev dependencies,
jetstream and the tools it installs among them, are development tools, so they
aren't checked.

A license is compared by SPDX ID, read from the package installed in the repo's
``.venv``: its License-Expression, or failing that its License, if that's an
expression of licenses licensing.md allows, or failing that its license
classifiers, if each names one license. A package whose metadata doesn't say clearly fails
until a review of its license file records the license in jetstream's
``python-licenses.toml``; a recorded package that later says clearly that it
has another license fails until it's reviewed again.

The export lists every platform's dependencies. One that isn't installed is
skipped if it has an environment marker, since it's for another platform, and
fails if it hasn't, since the ``.venv`` is out of date.

Usage, with the export on standard input, printing each package that fails
(exit 1)::

    uv export --frozen --no-dev --no-emit-project --no-hashes | python -m jetstream.python_licenses PYPROJECT
"""

from __future__ import annotations

import importlib.metadata
import re
import sys
import tomllib
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Final

from jetstream import npm_licenses

if TYPE_CHECKING:
    from collections.abc import Callable
    from email.message import Message
    from importlib.metadata import PackageMetadata

# The license classifiers that each name one license licensing.md allows. Any
# other, such as "BSD License", which doesn't say which BSD, isn't clear.
CLASSIFIER_IDS: Final[dict[str, str]] = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: MIT No Attribution License (MIT-0)": "MIT-0",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Zero-Clause BSD (0BSD)": "0BSD",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}

NAME: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
REVIEWED_FILE: Final[str] = "python-licenses.toml"


def canonical(name: str) -> str:
    """Return a package's name as PEP 503 normalizes it: ``Foo.Bar_baz`` is ``foo-bar-baz``."""
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    """Return the normalized package name a requirement such as ``foo[bar]>=1.0 ; marker`` starts with."""
    match: re.Match[str] | None = NAME.match(requirement.strip())
    if match is None:
        msg: str = f"not a requirement: {requirement!r}"
        raise ValueError(msg)
    return canonical(match.group())


def load_reviewed() -> dict[str, str]:
    """Return python-licenses.toml's reviewed licenses, by normalized package name."""
    reviewed: dict[str, str] = tomllib.loads((files("jetstream") / REVIEWED_FILE).read_text())["reviewed"]
    return {canonical(name): license_ for name, license_ in reviewed.items()}


def declared(metadata: PackageMetadata | Message) -> str | None:
    """Return the SPDX expression a package's ``metadata`` says clearly that it has, or None."""
    expression: str | None = metadata.get("License-Expression")
    if expression:
        return expression
    license_: str = metadata.get("License") or ""
    if npm_licenses.allows(license_, npm_licenses.ALLOWED_TRANSITIVE):
        return license_
    classifiers: list[str] = [line for line in metadata.get_all("Classifier") or [] if line.startswith("License :: ")]
    if not classifiers or not all(line in CLASSIFIER_IDS for line in classifiers):
        return None
    return " AND ".join(sorted({CLASSIFIER_IDS[line] for line in classifiers}))


def failures(
    dependencies: list[str],
    export: str,
    reviewed: dict[str, str],
    metadata: Callable[[str], PackageMetadata | Message] = importlib.metadata.metadata,
) -> list[str]:
    """Return a line for each package in ``export`` whose license isn't allowed; ``dependencies`` are the repo's direct ones."""
    direct: set[str] = {requirement_name(dependency) for dependency in dependencies}
    found: list[str] = []
    for line in export.splitlines():
        if not line or line[0].isspace() or line.startswith("#"):
            continue  # uv's comments
        name: str = requirement_name(line)
        try:
            package: PackageMetadata | Message = metadata(name)
        except importlib.metadata.PackageNotFoundError:
            if ";" not in line:
                found.append(f"{name}: isn't installed, so its license can't be read: run uv sync")
            continue
        where: str = f"{name} {package.get('Version')}"
        kind: str = "a direct" if name in direct else "a transitive"
        clear: str | None = declared(package)
        record: str | None = reviewed.get(name)
        if record is not None and clear is not None and clear != record:
            found.append(f"{where}: declares {clear}, but jetstream's {REVIEWED_FILE} records {record}: its license needs a review again")
        elif record is None and clear is None:
            found.append(f"{where}: its metadata doesn't say clearly which license it has: its license needs a review, in jetstream's {REVIEWED_FILE}")
        elif not npm_licenses.allows(record or clear or "", npm_licenses.ALLOWED if name in direct else npm_licenses.ALLOWED_TRANSITIVE):
            found.append(f"{where}: {record or clear} isn't allowed in {kind} product dependency")
    return found


def main(argv: list[str]) -> int:
    """Check the export on standard input against the pyproject.toml named in ``argv``, printing each failure; return 1 if there are any."""
    dependencies: list[str] = tomllib.loads(Path(argv[0]).read_text()).get("project", {}).get("dependencies", [])
    found: list[str] = failures(dependencies, sys.stdin.read(), load_reviewed())
    for line in found:
        sys.stdout.write(f"{line}\n")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
