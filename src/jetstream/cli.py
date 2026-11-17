"""The ``jetstream`` command: ``sync``, ``check`` and ``new-repo``."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Final

from jetstream import sync

EXIT_OK: Final[int] = 0
EXIT_DIFFERENT: Final[int] = 1  # check found differences
EXIT_ERROR: Final[int] = 2  # the repo's setup is wrong, e.g. no [tool.jetstream] packs
EXIT_NOT_IMPLEMENTED: Final[int] = 3

COMMANDS: Final[dict[str, str]] = {
    "sync": "write jetstream's owned files, pyproject.toml keys and .gitignore block",
    "check": "fail if anything differs from what sync would write",
    "new-repo": "create a new repo's first pyproject.toml, then sync",
}


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ``jetstream`` command."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="jetstream", description="Shared development infrastructure for Cloudfeaster repos.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('cloudfeaster-jetstream')}")
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    for name, help_text in COMMANDS.items():
        subparsers.add_parser(name, help=help_text, description=help_text)
    return parser


def run_sync(root: Path) -> int:
    """Write jetstream's files and keys into the repo, saying what changed."""
    changed: list[str] = sync.sync(root)
    for path in changed:
        print(f"jetstream sync: wrote {path}")
    return EXIT_OK


def run_check(root: Path) -> int:
    """Fail, naming each difference, if the repo differs from what sync would write."""
    found: list[str] = sync.check(root)
    if not found:
        return EXIT_OK
    for line in found:
        sys.stderr.write(f"*** jetstream: {line}\n")
    sys.stderr.write("*** jetstream: run `jetstream sync` and commit what it changes\n")
    return EXIT_DIFFERENT


def main(argv: list[str] | None = None) -> int:
    """Run the ``jetstream`` command and return its exit status."""
    args: argparse.Namespace = build_parser().parse_args(argv)
    if args.command == "new-repo":
        sys.stderr.write(f"*** jetstream: '{args.command}' isn't implemented yet\n")
        return EXIT_NOT_IMPLEMENTED
    try:
        root: Path = sync.repo_root()
        return run_sync(root) if args.command == "sync" else run_check(root)
    except sync.SyncError as e:
        sys.stderr.write(f"*** jetstream: {e}\n")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
