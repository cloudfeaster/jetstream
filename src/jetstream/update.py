"""The parts of ``run-update-jetstream.sh`` that read and write files (decision 23).

The script bumps a repo's jetstream pin to jetstream's latest release, runs
``jetstream sync``, and commits the result through GitHub's API, as the
jetstream update App, on the ``jetstream/update`` branch. It runs git, uv and
gh; this module runs no subprocess. Usage::

    python -I -m jetstream.update pin           # the pin's git URL and tag, tab-separated, or nothing
    python -I -m jetstream.update newer TAG     # from `git ls-remote --tags` on stdin, the latest tag if it's newer than TAG
    python -I -m jetstream.update set-pin TAG   # set the pin's tag in pyproject.toml
    python -I -m jetstream.update tree STATUS BASE_TREE  # a git/trees request for `git status --porcelain -z` output
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Final

import tomlkit

# The distribution whose pin the script bumps, in [tool.uv.sources].
DISTRIBUTION: Final[str] = "cloudfeaster-jetstream"

# A release tag, as release-please creates them (decision 9).
RELEASE_TAG: Final[re.Pattern[str]] = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
TAG_REF: Final[str] = "refs/tags/"

FILE_MODE: Final[str] = "100644"
EXECUTABLE_MODE: Final[str] = "100755"

EXIT_OK: Final[int] = 0
EXIT_ERROR: Final[int] = 2

USAGE: Final[str] = "usage: python -m jetstream.update pin | newer TAG | set-pin TAG | tree STATUS BASE_TREE\n"


class UpdateError(Exception):
    """A problem with the pin or the changes, reported in one line."""


def source(document: tomlkit.TOMLDocument) -> Any:  # noqa: ANN401 (a tomlkit table, or None)
    """Return the ``[tool.uv.sources]`` entry for jetstream, or None."""
    return document.get("tool", {}).get("uv", {}).get("sources", {}).get(DISTRIBUTION)


def pin(pyproject: str) -> tuple[str, str] | None:
    """Return the git URL and tag jetstream is pinned to, or None if it isn't pinned to a release tag."""
    entry: Any = source(tomlkit.parse(pyproject))
    if entry is None or "git" not in entry or not RELEASE_TAG.match(str(entry.get("tag", ""))):
        return None
    return str(entry["git"]), str(entry["tag"])


def version(tag: str) -> tuple[int, ...]:
    """Return a release tag's version, for comparison."""
    return tuple(int(part) for part in tag.removeprefix("v").split("."))


def newer(current: str, ls_remote: str) -> str | None:
    """Return the latest release tag in ``git ls-remote --tags`` output, if it's newer than ``current``."""
    tags: list[str] = [ref.removeprefix(TAG_REF) for line in ls_remote.splitlines() if (ref := line.partition("\t")[2]).startswith(TAG_REF)]
    releases: list[str] = [tag for tag in tags if RELEASE_TAG.match(tag)]
    latest: str | None = max(releases, key=version, default=None)
    return latest if latest is not None and version(latest) > version(current) else None


def set_pin(pyproject: str, tag: str) -> str:
    """Return ``pyproject`` with jetstream's pin set to ``tag``, keeping its comments and formatting."""
    document: tomlkit.TOMLDocument = tomlkit.parse(pyproject)
    entry: Any = source(document)
    if entry is None:
        msg: str = f"pyproject.toml has no [tool.uv.sources] {DISTRIBUTION}"
        raise UpdateError(msg)
    entry["tag"] = tag
    return tomlkit.dumps(document)


def tree(root: Path, status: bytes, base_tree: str) -> dict[str, Any]:
    """Return a ``POST git/trees`` request that makes ``base_tree`` match the changes ``git status --porcelain -z`` listed."""
    entries: list[dict[str, Any]] = []
    for record in status.decode().split("\0"):
        if not record:
            continue
        code: str = record[:2]
        path: str = record[3:]
        if "D" in code:
            entries.append({"path": path, "mode": FILE_MODE, "type": "blob", "sha": None})
            continue
        file: Path = root / path
        try:
            content: str = file.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            msg: str = f"{path}: not UTF-8 text, so it can't be committed through the trees API"
            raise UpdateError(msg) from e
        mode: str = EXECUTABLE_MODE if file.stat().st_mode & 0o111 else FILE_MODE
        entries.append({"path": path, "mode": mode, "type": "blob", "content": content})
    return {"base_tree": base_tree, "tree": entries}


def main(argv: list[str] | None = None) -> int:
    """Run ``python -m jetstream.update`` and return its exit status."""
    pyproject: Path = Path.cwd() / "pyproject.toml"
    try:
        match sys.argv[1:] if argv is None else argv:
            case ["pin"]:
                found: tuple[str, str] | None = pin(pyproject.read_text())
                if found is not None:
                    sys.stdout.write("\t".join(found) + "\n")
            case ["newer", current] if RELEASE_TAG.match(current):
                latest: str | None = newer(current, sys.stdin.read())
                if latest is not None:
                    sys.stdout.write(f"{latest}\n")
            case ["set-pin", tag] if RELEASE_TAG.match(tag):
                pyproject.write_text(set_pin(pyproject.read_text(), tag))
            case ["tree", status, base_tree]:
                sys.stdout.write(json.dumps(tree(Path.cwd(), Path(status).read_bytes(), base_tree)) + "\n")
            case _:
                sys.stderr.write(USAGE)
                return EXIT_ERROR
    except UpdateError as e:
        sys.stderr.write(f"*** jetstream update: {e}\n")
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
