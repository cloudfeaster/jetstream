"""The ``jetstream`` command: ``sync``, ``check`` and ``new-repo``."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from typing import Final

EXIT_NOT_IMPLEMENTED: Final[int] = 2

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


def main(argv: list[str] | None = None) -> int:
    """Run the ``jetstream`` command and return its exit status."""
    args: argparse.Namespace = build_parser().parse_args(argv)
    sys.stderr.write(f"*** jetstream: '{args.command}' isn't implemented yet\n")
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":
    sys.exit(main())
