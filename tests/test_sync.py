"""Tests for ``jetstream sync`` and ``jetstream check``, each in a throwaway git repo."""

import subprocess
import tomllib
from pathlib import Path
from typing import Any, Final

import pytest

from jetstream import cli, sync

ROOT: Final[Path] = Path(__file__).parent.parent

PYPROJECT: Final[str] = """\
[project]
name = "example"  # the repo's name
version = "0.1.0"
requires-python = "==3.13.*"
dependencies = []

[tool.jetstream]
packs = ["core"]
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with a pyproject.toml selecting the core pack, never synced."""
    repo: Path = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True)  # noqa: S607
    (repo / "pyproject.toml").write_text(PYPROJECT)
    return repo


@pytest.fixture
def synced(repo: Path) -> Path:
    sync.sync(repo)
    return repo


def pyproject_of(repo: Path) -> dict[str, Any]:
    return tomllib.loads((repo / "pyproject.toml").read_text())


# --- [tool.jetstream] packs


@pytest.mark.parametrize(
    ("packs", "message"),
    [
        (None, "pyproject.toml needs [tool.jetstream] packs"),
        ('"core"', "pyproject.toml needs [tool.jetstream] packs"),
        ('["core", "rust"]', "unknown pack(s) in [tool.jetstream] packs: rust"),
        ('["python"]', 'packs must include "core"'),
    ],
)
def test_read_packs_rejects_bad_packs(repo: Path, packs: str | None, message: str) -> None:
    text: str = PYPROJECT.replace('packs = ["core"]', "" if packs is None else f"packs = {packs}")
    (repo / "pyproject.toml").write_text(text)
    with pytest.raises(sync.SyncError, match=message.replace("[", r"\[").replace("(", r"\(").replace(")", r"\)")):
        sync.read_packs(repo)


def test_read_packs_puts_packs_in_order(repo: Path) -> None:
    (repo / "pyproject.toml").write_text(PYPROJECT.replace('["core"]', '["website", "core", "python"]'))
    assert sync.read_packs(repo) == ("core", "python", "website")


def test_read_packs_needs_a_pyproject(tmp_path: Path) -> None:
    with pytest.raises(sync.SyncError, match="no pyproject.toml"):
        sync.read_packs(tmp_path)


# --- what core owns


def test_core_owns_its_files() -> None:
    want: sync.Expected = sync.expected(("core",))
    assert set(want.files) == {
        ".claude/settings.json",
        ".github/dependabot.yml",
        ".github/workflows/jetstream-lint.yaml",
        ".jetstream/docs/core/dco.md",
        ".jsonlintignore",
        ".pre-commit-config.yaml",
        ".shellcheckrc",
        ".trivy.yaml",
        ".vscode/.gitignore",
        ".vscode/settings.json",
        ".vscode/terminal-init.sh",
        ".yamllint",
        "cfg4dev.sh",
        "mado.toml",
    }
    assert want.files["cfg4dev.sh"].executable
    assert want.files[".jetstream/docs/core/dco.md"].content.decode().startswith(sync.DOC_HEADER + "# Developer Certificate of Origin")
    assert "entry: jetstream check" in want.files[".pre-commit-config.yaml"].content.decode()
    assert want.gitignore_block.startswith(sync.GITIGNORE_START + "\n")
    assert want.gitignore_block.endswith(sync.GITIGNORE_END + "\n")
    assert want.pyproject_keys[("tool", "uv", "exclude-newer")] == "7 days"


# --- sync, then check


def test_sync_writes_everything_and_check_then_passes(repo: Path) -> None:
    assert sync.check(repo) != []
    changed: list[str] = sync.sync(repo)
    assert ".pre-commit-config.yaml" in changed
    assert ".gitignore" in changed
    assert "pyproject.toml" in changed
    assert sync.check(repo) == []
    assert sync.sync(repo) == []  # nothing left to change


def test_sync_adds_missing_keys_and_keeps_the_repos(repo: Path) -> None:
    sync.sync(repo)
    text: str = (repo / "pyproject.toml").read_text()
    assert text.startswith(PYPROJECT)  # the repo's keys and comments are untouched
    assert "[tool]\n" not in text  # no empty super-table header
    config: dict[str, Any] = pyproject_of(repo)
    assert config["tool"]["uv"] == {"required-version": ">=0.13.5", "exclude-newer": "7 days"}
    assert config["tool"]["pytest"]["ini_options"]["markers"] == [
        "integration: slow tests that run-unit-tests.sh leaves out",
    ]


def test_check_names_a_wrong_key_and_sync_fixes_only_that(synced: Path) -> None:
    pyproject: Path = synced / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace('exclude-newer = "7 days"', 'exclude-newer = "1 day"  # faster'))
    assert sync.check(synced) == ['pyproject.toml: [tool.uv] exclude-newer is "1 day"; jetstream sets "7 days"']

    assert sync.sync(synced) == ["pyproject.toml"]
    assert pyproject_of(synced)["tool"]["uv"]["exclude-newer"] == "7 days"
    assert sync.check(synced) == []


def test_a_repo_can_add_keys_to_jetstreams_tables(synced: Path) -> None:
    pyproject: Path = synced / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace("[tool.uv]\n", '[tool.uv]\ncache-keys = [{file = "x"}]\n'))
    assert sync.check(synced) == []
    assert sync.sync(synced) == []


def test_check_names_a_missing_key(synced: Path) -> None:
    pyproject: Path = synced / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace('required-version = ">=0.13.5"\n', ""))
    assert sync.check(synced) == ['pyproject.toml: [tool.uv] required-version is missing; jetstream sets ">=0.13.5"']


def test_check_names_changed_missing_and_non_executable_files(synced: Path) -> None:
    (synced / "mado.toml").write_text("changed\n")
    (synced / ".yamllint").unlink()
    (synced / "cfg4dev.sh").chmod(0o644)
    assert sync.check(synced) == [
        ".yamllint is missing",
        "cfg4dev.sh isn't executable",
        "mado.toml differs from what jetstream writes",
    ]
    assert sorted(sync.sync(synced)) == [".yamllint", "cfg4dev.sh", "mado.toml"]
    assert sync.check(synced) == []


def test_sync_deletes_jetstream_workflows_the_release_does_not_write(synced: Path) -> None:
    workflows: Path = synced / ".github" / "workflows"  # sync wrote jetstream-lint.yaml there
    (workflows / "jetstream-old.yaml").write_text("old\n")
    (workflows / "deploy.yaml").write_text("the repo's own\n")
    assert sync.check(synced) == [".github/workflows/jetstream-old.yaml isn't written by this jetstream release"]

    assert sync.sync(synced) == [".github/workflows/jetstream-old.yaml (deleted)"]
    assert not (workflows / "jetstream-old.yaml").exists()
    assert (workflows / "deploy.yaml").exists()


def test_sync_replaces_the_docs_as_a_whole(synced: Path) -> None:
    docs: Path = synced / ".jetstream" / "docs"
    (docs / "core" / "dco.md").write_text("edited\n")
    (docs / "core" / "old.md").write_text("# Old\n")
    (docs / "retired").mkdir()
    (docs / "retired" / "gone.md").write_text("# Gone\n")
    assert sync.check(synced) == [
        ".jetstream/docs/core/dco.md differs from what jetstream writes",
        ".jetstream/docs/core/old.md isn't written by this jetstream release",
        ".jetstream/docs/retired/gone.md isn't written by this jetstream release",
    ]

    assert sync.sync(synced) == [
        ".jetstream/docs/core/dco.md",
        ".jetstream/docs/core/old.md (deleted)",
        ".jetstream/docs/retired/gone.md (deleted)",
    ]
    assert sorted(path.relative_to(docs).as_posix() for path in docs.rglob("*")) == ["core", "core/dco.md"]
    assert sync.check(synced) == []


# --- .gitignore


def test_sync_puts_the_block_first_and_keeps_the_repos_lines(repo: Path) -> None:
    (repo / ".gitignore").write_text("/output/\n")
    sync.sync(repo)
    text: str = (repo / ".gitignore").read_text()
    assert text == sync.expected(("core",)).gitignore_block + "\n/output/\n"


def test_sync_replaces_only_the_block(synced: Path) -> None:
    gitignore: Path = synced / ".gitignore"
    block: str = gitignore.read_text()
    gitignore.write_text("/before/\n" + block.replace(".venv/\n", "") + "/after/\n")
    assert sync.check(synced) == [".gitignore's jetstream block differs from what jetstream writes"]

    sync.sync(synced)
    assert gitignore.read_text() == "/before/\n" + block + "/after/\n"


def test_check_needs_the_block(synced: Path) -> None:
    (synced / ".gitignore").write_text("/output/\n")
    assert sync.check(synced) == [".gitignore has no jetstream block"]


@pytest.mark.parametrize(
    "text",
    [
        "# >>> jetstream\n.venv/\n",  # no end
        "# <<< jetstream\n# >>> jetstream\n",  # wrong order
        "# >>> jetstream\n# <<< jetstream\n# >>> jetstream\n# <<< jetstream\n",  # two blocks
    ],
)
def test_bad_gitignore_markers_are_an_error(synced: Path, text: str) -> None:
    (synced / ".gitignore").write_text(text)
    with pytest.raises(sync.SyncError, match="exactly one"):
        sync.sync(synced)


# --- the command


def test_check_command_names_each_difference(synced: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(synced)
    (synced / "mado.toml").write_text("changed\n")
    assert cli.main(["check"]) == cli.EXIT_DIFFERENT
    err: str = capsys.readouterr().err
    assert "*** jetstream: mado.toml differs from what jetstream writes\n" in err
    assert "run `jetstream sync`" in err


def test_sync_command_says_what_it_wrote(synced: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(synced / ".")
    (synced / "mado.toml").unlink()
    assert cli.main(["sync"]) == cli.EXIT_OK
    assert capsys.readouterr().out == "jetstream sync: wrote mado.toml\n"
    assert cli.main(["check"]) == cli.EXIT_OK


def test_commands_report_setup_errors_in_one_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(["check"]) == cli.EXIT_ERROR
    assert capsys.readouterr().err == "*** jetstream: not in a git repo\n"


def test_jetstream_passes_its_own_check() -> None:
    assert sync.check(ROOT) == [], "run jetstream sync"
