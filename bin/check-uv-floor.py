#!/usr/bin/env python3
"""Check the uv floor every repo gets from core, ``[tool.uv] required-version``.

    bin/check-uv-floor.py      fail if the floor needs changing
    bin/check-uv-floor.py -v   ... and report the floor and Dependabot's uv

Dependabot runs ``uv lock`` with the uv pinned in dependabot-core's uv
Dockerfile, so a floor above that uv makes every Dependabot uv update fail.
A floor a minor version or more behind it has fallen behind uv: bump it to
Dependabot's uv, which uv releases are known to work with Dependabot.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Final

CORE_PYPROJECT: Final[Path] = Path(__file__).resolve().parent.parent / "src" / "jetstream" / "parts" / "core" / "pyproject.toml"
DOCKERFILE_URL: Final[str] = "https://raw.githubusercontent.com/dependabot/dependabot-core/main/uv/Dockerfile"
TIMEOUT_SECONDS: Final[int] = 30
FLOOR: Final[re.Pattern[str]] = re.compile(r"^>=(\d+)\.(\d+)\.(\d+)$")
DEPENDABOT_UV: Final[re.Pattern[str]] = re.compile(r"ghcr\.io/astral-sh/uv:(\d+)\.(\d+)\.(\d+)\b")

Version = tuple[int, int, int]


class FloorError(Exception):
    """A problem to report in one line."""


def as_text(version: Version) -> str:
    """Return ``version`` as ``X.Y.Z``."""
    return ".".join(str(part) for part in version)


def floor(pyproject: str) -> Version:
    """Return the version in core's ``required-version = ">=X.Y.Z"``."""
    required: object = tomllib.loads(pyproject).get("tool", {}).get("uv", {}).get("required-version")
    match: re.Match[str] | None = FLOOR.match(required) if isinstance(required, str) else None
    if match is None:
        msg: str = f"core's required-version is {required!r}, not a '>=X.Y.Z' floor"
        raise FloorError(msg)
    return (int(match[1]), int(match[2]), int(match[3]))


def dependabot_uv(dockerfile: str) -> Version:
    """Return the uv version dependabot-core's uv Dockerfile copies uv from."""
    versions: set[Version] = {(int(m[1]), int(m[2]), int(m[3])) for m in DEPENDABOT_UV.finditer(dockerfile)}
    if len(versions) != 1:
        msg: str = f"expected one ghcr.io/astral-sh/uv:X.Y.Z image in {DOCKERFILE_URL}, found {len(versions)}"
        raise FloorError(msg)
    return versions.pop()


def fetch_dockerfile() -> str:
    """Return dependabot-core's uv Dockerfile."""
    try:
        with urllib.request.urlopen(DOCKERFILE_URL, timeout=TIMEOUT_SECONDS) as response:  # nosec B310
            return response.read().decode()
    except urllib.error.URLError as e:
        msg: str = f"{DOCKERFILE_URL}: {e.reason}"
        raise FloorError(msg) from e


def problem(ours: Version, dependabot: Version) -> str | None:
    """Return what's wrong with the floor ``ours``, given Dependabot's uv, if anything."""
    if ours > dependabot:
        return f"uv floor {as_text(ours)} is above Dependabot's uv {as_text(dependabot)}, so Dependabot's uv lock fails: lower it to {as_text(dependabot)}"
    if ours[:2] < dependabot[:2]:
        return f"uv floor {as_text(ours)} is a minor version behind Dependabot's uv {as_text(dependabot)}: raise it to {as_text(dependabot)}"
    return None


def main(argv: list[str] | None = None) -> int:
    """Check the floor; return the exit status."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", help="report the floor and Dependabot's uv")
    args: argparse.Namespace = parser.parse_args(argv)
    try:
        ours: Version = floor(CORE_PYPROJECT.read_text())
        dependabot: Version = dependabot_uv(fetch_dockerfile())
    except FloorError as e:
        sys.stderr.write(f"*** {e}\n")
        return 1
    if args.verbose:
        sys.stdout.write(f"uv floor {as_text(ours)}, Dependabot's uv {as_text(dependabot)}\n")
    found: str | None = problem(ours, dependabot)
    if found:
        sys.stderr.write(f"*** {found}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
