"""Tests for the ``jetstream`` command's argument handling."""

from importlib.metadata import version

import pytest

from jetstream import cli


def test_new_repo_is_not_implemented_yet(capsys: pytest.CaptureFixture[str]) -> None:
    """``jetstream new-repo`` says it isn't implemented yet, with its own exit status."""
    assert cli.main(["new-repo"]) == cli.EXIT_NOT_IMPLEMENTED
    assert "'new-repo' isn't implemented yet" in capsys.readouterr().err


def test_a_command_is_required() -> None:
    """``jetstream`` with no command is a usage error."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code == 2  # argparse's usage-error status  # noqa: PLR2004


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    """``jetstream --version`` prints the installed package's version."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
    assert exc_info.value.code == 0
    # release-please bumps the version, so don't hard-code it
    assert capsys.readouterr().out.startswith(f"jetstream {version('cloudfeaster-jetstream')}")
