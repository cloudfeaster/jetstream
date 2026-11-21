"""Tests for the ``jetstream`` command's argument handling."""

from importlib.metadata import version
from typing import Final

import pytest

from jetstream import cli

USAGE_ERROR: Final[int] = 2  # argparse's exit status for a usage error


def test_a_command_is_required() -> None:
    """``jetstream`` with no command is a usage error."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code == USAGE_ERROR


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    """``jetstream --version`` prints the installed package's version."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
    assert exc_info.value.code == 0
    # release-please bumps the version, so don't hard-code it
    assert capsys.readouterr().out.startswith(f"jetstream {version('cloudfeaster-jetstream')}")
