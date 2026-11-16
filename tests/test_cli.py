"""Tests for the ``jetstream`` command's argument handling."""

import pytest

from jetstream import cli


@pytest.mark.parametrize("command", ["sync", "check", "new-repo"])
def test_commands_are_not_implemented_yet(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([command]) == cli.EXIT_NOT_IMPLEMENTED
    assert f"'{command}' isn't implemented yet" in capsys.readouterr().err


def test_a_command_is_required() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code == 2  # argparse's usage-error status  # noqa: PLR2004


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.startswith("jetstream 0.0.0")
