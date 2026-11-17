"""Tests for the ``jetstream`` command's argument handling."""

import pytest

from jetstream import cli


def test_new_repo_is_not_implemented_yet(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["new-repo"]) == cli.EXIT_NOT_IMPLEMENTED
    assert "'new-repo' isn't implemented yet" in capsys.readouterr().err


def test_a_command_is_required() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code == 2  # argparse's usage-error status  # noqa: PLR2004


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.startswith("jetstream 0.0.0")
