"""Tests for ``jetstream new-repo``."""

import tomllib
from importlib.metadata import version
from pathlib import Path
from typing import Any, Final

import pytest

from jetstream import cli, new_repo, sync

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DESCRIPTION: Final[str] = 'A "quoted" description'
USAGE_ERROR: Final[int] = 2  # argparse's exit status for a usage error


@pytest.fixture
def empty(tmp_path: Path) -> Path:
    """Return an empty git repo, named my-repo."""
    repo: Path = tmp_path / "my-repo"
    (repo / ".git").mkdir(parents=True)
    return repo


def pyproject_of(repo: Path) -> dict[str, Any]:
    """Return ``repo``'s parsed pyproject.toml."""
    return tomllib.loads((repo / "pyproject.toml").read_text())


@pytest.mark.parametrize("packs", [("core",), ("core", "python")])
def test_new_repo_passes_check(empty: Path, packs: tuple[str, ...]) -> None:
    """A new repo has every file jetstream owns, so ``jetstream check`` passes straight away."""
    new_repo.new_repo(empty, DESCRIPTION, packs)
    assert sync.check(empty) == []


def test_core_repo_is_not_a_package_and_pins_this_release(empty: Path) -> None:
    """A core repo pins the jetstream release that made it, and isn't a Python package."""
    new_repo.new_repo(empty, DESCRIPTION, ("core",))
    config: dict[str, Any] = pyproject_of(empty)
    assert config["project"]["name"] == "my-repo"
    assert config["project"]["description"] == DESCRIPTION
    assert config["dependency-groups"]["dev"] == ["cloudfeaster-jetstream[core]"]
    assert config["tool"]["uv"]["package"] is False
    assert config["tool"]["uv"]["sources"]["cloudfeaster-jetstream"] == {"git": new_repo.JETSTREAM_GIT, "tag": f"v{version('cloudfeaster-jetstream')}"}
    assert config["tool"]["jetstream"]["packs"] == ["core"]
    assert "build-system" not in config
    assert not (empty / ".pip-audit-ignore").exists()
    assert (empty / ".trivyignore").is_file()


def test_python_repo_is_a_package(empty: Path) -> None:
    """A python repo builds a package with hatchling, and gets a .pip-audit-ignore starter."""
    new_repo.new_repo(empty, DESCRIPTION, ("python",), name="My.Repo")
    config: dict[str, Any] = pyproject_of(empty)
    assert config["build-system"] == {"requires": [new_repo.HATCHLING], "build-backend": "hatchling.build"}
    assert config["project"]["urls"] == {"Repository": f"{new_repo.ORG_URL}/My.Repo"}
    assert config["dependency-groups"]["dev"] == ["cloudfeaster-jetstream[core,python]"]
    assert config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["my_repo"]
    assert "package" not in config["tool"]["uv"]
    assert config["tool"]["jetstream"]["packs"] == ["core", "python"]
    assert (empty / "my_repo" / "__init__.py").read_text().startswith('"""')
    assert (empty / ".pip-audit-ignore").read_text().startswith("# ")


def test_hatchling_pin_matches_jetstreams_own() -> None:
    """A new python repo starts on the hatchling jetstream itself builds with."""
    config: dict[str, Any] = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert config["build-system"]["requires"] == [new_repo.HATCHLING]


def test_claude_md_imports_the_docs_for_working_in_the_repo() -> None:
    """CLAUDE.md imports every doc jetstream writes for the packs, except those for setting a repo up, behavioral guidelines first."""
    text: str = new_repo.claude_md(("core", "python"))
    imports: list[str] = [line.removeprefix("@") for line in text.splitlines() if line.startswith("@")]
    docs: set[str] = {path for path in sync.expected(("core", "python")).files if path.startswith(".jetstream/docs/")}
    assert set(imports) == {path for path in docs if path.rsplit("/", 1)[-1] not in new_repo.SETUP_DOCS}
    assert imports[0] == ".jetstream/docs/core/behavioral-guidelines.md"
    assert imports[-1] == ".jetstream/docs/python/python.md"


def test_new_repo_writes_nothing_into_a_repo_that_has_files(empty: Path) -> None:
    """new-repo refuses a repo that already has one of its files, and changes nothing."""
    (empty / "README.md").write_text("# mine\n")
    with pytest.raises(new_repo.NewRepoError, match=r"already has README\.md"):
        new_repo.new_repo(empty, DESCRIPTION, ("core",))
    assert sorted(path.name for path in empty.iterdir()) == [".git", "README.md"]


@pytest.mark.parametrize(
    ("description", "packs", "name", "message"),
    [
        (DESCRIPTION, ("core", "website"), None, "the website pack isn't ready"),
        (" ", ("core",), None, "description can't be empty"),
        (DESCRIPTION, ("core",), "bad name", "isn't a valid project name"),
        (DESCRIPTION, ("core", "python"), "1st-repo", "can't be a Python package name"),
    ],
)
def test_new_repo_rejects_bad_inputs(empty: Path, description: str, packs: tuple[str, ...], name: str | None, message: str) -> None:
    """new-repo explains, in one line, why it can't start the repo."""
    with pytest.raises(new_repo.NewRepoError, match=message):
        new_repo.new_repo(empty, description, packs, name=name)
    assert [path.name for path in empty.iterdir()] == [".git"]


def test_cli_new_repo_prints_what_it_wrote_and_the_next_steps(empty: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """``jetstream new-repo`` writes the repo, lists each file once, and says what's left to do."""
    monkeypatch.chdir(empty)
    assert cli.main(["new-repo", "--description", DESCRIPTION, "--pack", "python"]) == cli.EXIT_OK
    out: str = capsys.readouterr().out
    assert out.count("jetstream new-repo: wrote pyproject.toml\n") == 1
    assert "jetstream new-repo: wrote cfg4dev.sh\n" in out
    assert "source cfg4dev.sh" in out
    assert "custom property" in out


def test_cli_new_repo_reports_an_error(empty: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """``jetstream new-repo`` reports a problem in one line, with the error exit status."""
    monkeypatch.chdir(empty)
    assert cli.main(["new-repo", "--description", DESCRIPTION, "--pack", "website"]) == cli.EXIT_ERROR
    assert capsys.readouterr().err == "*** jetstream: the website pack isn't ready for new repos yet\n"


def test_cli_new_repo_needs_a_description() -> None:
    """``jetstream new-repo`` without ``--description`` is a usage error."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["new-repo"])
    assert exc_info.value.code == USAGE_ERROR
