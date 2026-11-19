"""Tests for jetstream.prune, the TOML half of the prune checks."""

from pathlib import Path
from typing import Final

import pytest

from jetstream import prune

PYPROJECT: Final[str] = """\
[project]
name = "a"

[tool.uv]
exclude-newer = "7 days"
constraint-dependencies = [
    "jinja2>=3.1.6",  # CVE-2025-27516
    "Foo.Bar >= 2.0",
]
exclude-newer-package = { boto3 = "2026-11-19T00:00:00Z", flask = "2026-11-19T00:00:00Z" }
"""


@pytest.fixture
def pyproject(tmp_path: Path) -> Path:
    """Return a pyproject.toml with two constraints and two overrides."""
    path: Path = tmp_path / "pyproject.toml"
    path.write_text(PYPROJECT)
    return path


def test_constraints_are_listed_in_order(pyproject: Path) -> None:
    """Each constraint is listed as written."""
    assert prune.constraints(pyproject) == ["jinja2>=3.1.6", "Foo.Bar >= 2.0"]


def test_no_uv_table_means_nothing_to_check(tmp_path: Path) -> None:
    """A pyproject.toml without [tool.uv] has no constraints or overrides."""
    path: Path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nname = "a"\n')
    assert prune.constraints(path) == []
    assert prune.exclude_newer_packages(path) == []


def test_invert_turns_a_floor_into_its_opposite() -> None:
    """``foo>=1.2.3`` becomes ``foo<1.2.3``, whatever the spacing."""
    assert prune.invert("jinja2>=3.1.6") == "jinja2<3.1.6"
    assert prune.invert("Foo.Bar >= 2.0") == "Foo.Bar<2.0"


@pytest.mark.parametrize("spec", ["jinja2==3.1.6", "jinja2>=3.1.6,<4", "jinja2", "jinja2>=3.1.6; python_version < '3.14'"])
def test_invert_rejects_anything_but_a_floor(spec: str) -> None:
    """Only a plain floor can be checked, so anything else is an error naming it."""
    with pytest.raises(prune.PruneError, match="isn't a floor"):
        prune.invert(spec)


def test_invert_constraint_changes_only_that_entry(pyproject: Path) -> None:
    """The constraint is replaced by its inverse; its comment and everything else stay as they were."""
    assert prune.invert_constraint(pyproject, 0) == "jinja2<3.1.6"
    assert pyproject.read_text() == PYPROJECT.replace('"jinja2>=3.1.6"', '"jinja2<3.1.6"')


def test_remove_exclude_newer_package_removes_only_that_override(pyproject: Path) -> None:
    """The override is removed, and the other one stays."""
    assert prune.exclude_newer_packages(pyproject) == ["boto3", "flask"]
    prune.remove_exclude_newer_package(pyproject, "boto3")
    assert prune.exclude_newer_packages(pyproject) == ["flask"]
    assert 'flask = "2026-11-19T00:00:00Z"' in pyproject.read_text()


def test_locked_versions_match_names_as_uv_writes_them(tmp_path: Path) -> None:
    """A package is found by its normalized name, with every version it's locked at."""
    uv_lock: Path = tmp_path / "uv.lock"
    uv_lock.write_text(
        'version = 1\n\n[[package]]\nname = "foo-bar"\nversion = "2.0"\n\n[[package]]\nname = "foo-bar"\nversion = "1.0"\n\n[[package]]\nname = "a"\nsource = { virtual = "." }\n',
    )
    assert prune.locked_versions(uv_lock, "Foo.Bar") == ["1.0", "2.0"]
    assert prune.locked_versions(uv_lock, "a") == []  # the project itself has no version
    assert prune.locked_versions(uv_lock, "missing") == []


def test_main_prints_one_item_per_line(pyproject: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Each command prints its items, one per line."""
    assert prune.main(["constraints", str(pyproject)]) == prune.EXIT_OK
    assert capsys.readouterr().out == "jinja2>=3.1.6\nFoo.Bar >= 2.0\n"


def test_main_reports_a_bad_command(capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown command, or the wrong number of arguments, is an error with the usage."""
    assert prune.main(["constraints"]) == prune.EXIT_ERROR
    assert "usage: python -m jetstream.prune" in capsys.readouterr().err
