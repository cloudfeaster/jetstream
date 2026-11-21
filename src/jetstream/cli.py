"""The ``jetstream`` command: ``sync``, ``check`` and ``new-repo``."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from typing import TYPE_CHECKING, Final

from jetstream import new_repo, sync

if TYPE_CHECKING:
    from pathlib import Path

EXIT_OK: Final[int] = 0
EXIT_DIFFERENT: Final[int] = 1  # check found differences
EXIT_ERROR: Final[int] = 2  # the repo's setup is wrong, e.g. no [tool.jetstream] packs

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
        subparser: argparse.ArgumentParser = subparsers.add_parser(name, help=help_text, description=help_text)
        if name == "new-repo":
            subparser.add_argument("--description", required=True, help="what the repo is, for pyproject.toml and README.md")
            subparser.add_argument("--name", help="the project's name (default: the repo folder's name)")
            subparser.add_argument("--pack", action="append", default=[], choices=[pack for pack in sync.PACKS if pack != "core"], help="a pack besides core; repeat for more")
    return parser


def run_sync(root: Path) -> int:
    """Write jetstream's files and keys into the repo, saying what changed."""
    changed: list[str] = sync.sync(root)
    for path in changed:
        sys.stdout.write(f"jetstream sync: wrote {path}\n")
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


# What new-repo leaves to do, after it writes the files.
NEXT_STEPS: Final[str] = """
Next, in this repo:
  1. source cfg4dev.sh            # uv sync (writes uv.lock), installs the tools and the pre-commit hooks
  2. pre-commit run --all-files
  3. commit on a branch and open a pull request (.jetstream/docs/core/dev-workflow.md)

An org owner (.jetstream/docs/core/new-repo.md):
  - sets the repo's jetstream custom property to true, before that pull request merges, if it isn't already
  - once it merges, sets up its Dependabot alert sync (.jetstream/docs/core/dependabot-alerts.md, "Adding a repo")
  - and its jetstream updates (.jetstream/docs/core/jetstream-update.md, "Adding a repo")
"""


def run_new_repo(root: Path, args: argparse.Namespace) -> int:
    """Write a new repo's first files, then sync, and say what's left to do."""
    for path in new_repo.new_repo(root, args.description, ("core", *args.pack), args.name):
        sys.stdout.write(f"jetstream new-repo: wrote {path}\n")
    sys.stdout.write(NEXT_STEPS)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Run the ``jetstream`` command and return its exit status."""
    args: argparse.Namespace = build_parser().parse_args(argv)
    try:
        root: Path = sync.repo_root()
        if args.command == "new-repo":
            return run_new_repo(root, args)
        return run_sync(root) if args.command == "sync" else run_check(root)
    except (sync.SyncError, new_repo.NewRepoError) as e:
        sys.stderr.write(f"*** jetstream: {e}\n")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
