"""Tests for bin/check-uv-floor.py."""

import importlib.machinery
import importlib.util
import types
from pathlib import Path
from typing import Final

import pytest

_spec: importlib.machinery.ModuleSpec | None = importlib.util.spec_from_file_location("check_uv_floor", Path(__file__).parent.parent / "bin" / "check-uv-floor.py")
assert _spec is not None
assert _spec.loader is not None
check_uv_floor: types.ModuleType = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_uv_floor)

DOCKERFILE: Final[str] = "FROM docker.io/library/ubuntu:24.04\nFROM ghcr.io/astral-sh/uv:0.13.7 AS uv\nCOPY --from=uv /uv /uvx /usr/local/bin/\n"


@pytest.mark.parametrize(
    ("ours", "dependabot", "expected"),
    [
        ((0, 13, 5), (0, 13, 7), None),
        ((0, 13, 7), (0, 13, 7), None),
        ((0, 13, 8), (0, 13, 7), "above Dependabot's uv 0.13.7, so Dependabot's uv lock fails: lower it to 0.13.7"),
        ((0, 13, 5), (0, 14, 0), "a minor version behind Dependabot's uv 0.14.0: raise it to 0.14.0"),
        ((0, 13, 5), (1, 0, 0), "a minor version behind Dependabot's uv 1.0.0: raise it to 1.0.0"),
    ],
)
def test_problem(ours: tuple[int, int, int], dependabot: tuple[int, int, int], expected: str | None) -> None:
    """The floor fails above Dependabot's uv, and a minor version or more behind it."""
    found: str | None = check_uv_floor.problem(ours, dependabot)
    if expected is None:
        assert found is None
    else:
        assert found is not None
        assert expected in found


def test_floor_reads_cores_required_version() -> None:
    """The floor is read from core's part, the one every repo gets."""
    assert check_uv_floor.floor('[tool.uv]\nrequired-version = ">=0.13.5"\n') == (0, 13, 5)
    assert check_uv_floor.floor(check_uv_floor.CORE_PYPROJECT.read_text())


@pytest.mark.parametrize("required", ["==0.13.5", ">=0.13", None])
def test_floor_must_be_a_floor(required: str | None) -> None:
    """A required-version that isn't '>=X.Y.Z' is reported, not guessed at."""
    pyproject: str = f'[tool.uv]\nrequired-version = "{required}"\n' if required else "[tool.uv]\n"
    with pytest.raises(check_uv_floor.FloorError, match=r"not a '>=X\.Y\.Z' floor"):
        check_uv_floor.floor(pyproject)


def test_dependabot_uv() -> None:
    """Dependabot's uv is the uv image its Dockerfile copies uv from."""
    assert check_uv_floor.dependabot_uv(DOCKERFILE) == (0, 13, 7)


@pytest.mark.parametrize("dockerfile", ["FROM docker.io/library/ubuntu:24.04\n", DOCKERFILE + "FROM ghcr.io/astral-sh/uv:0.13.8\n"])
def test_dependabot_uv_must_be_one_version(dockerfile: str) -> None:
    """A Dockerfile with no uv image, or more than one version, is reported rather than guessed at."""
    with pytest.raises(check_uv_floor.FloorError, match="expected one"):
        check_uv_floor.dependabot_uv(dockerfile)


@pytest.mark.parametrize(("dockerfile", "status"), [(DOCKERFILE, 0), (DOCKERFILE.replace("0.13.7", "0.14.1"), 1)])
def test_main(dockerfile: str, status: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The check reports the versions with --verbose, and fails when the floor needs changing."""
    pyproject: Path = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.uv]\nrequired-version = ">=0.13.5"\n')
    monkeypatch.setattr(check_uv_floor, "CORE_PYPROJECT", pyproject)
    monkeypatch.setattr(check_uv_floor, "fetch_dockerfile", lambda: dockerfile)
    assert check_uv_floor.main(["--verbose"]) == status
    out, err = capsys.readouterr()
    assert out.startswith("uv floor 0.13.5, Dependabot's uv ")
    assert ("raise it to 0.14.1" in err) == bool(status)
