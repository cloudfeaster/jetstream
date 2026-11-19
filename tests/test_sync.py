"""Tests for ``jetstream sync`` and ``jetstream check``, each in a throwaway git repo."""

import os
import subprocess
import tomllib
from pathlib import Path
from typing import Any, Final

import pytest
import yaml

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


def git(repo: Path, *args: str) -> None:
    """Run git in ``repo``, without the GIT_* variables a git hook sets (such as GIT_INDEX_FILE), which would point it at this repo."""
    env: dict[str, str] = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    subprocess.run(["git", *args], cwd=repo, env=env, check=True)  # noqa: S603, S607 (only the tests' own arguments; git from PATH, as people run it)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Return a git repo with a pyproject.toml selecting the core pack, never synced."""
    repo: Path = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet")
    (repo / "pyproject.toml").write_text(PYPROJECT)
    return repo


@pytest.fixture
def synced(repo: Path) -> Path:
    """Return ``repo`` after ``jetstream sync``."""
    sync.sync(repo)
    return repo


def pyproject_of(repo: Path) -> dict[str, Any]:
    """Return ``repo``'s parsed pyproject.toml."""
    return tomllib.loads((repo / "pyproject.toml").read_text())


# --- the repo's root


def test_repo_root_is_found_from_a_subfolder(repo: Path) -> None:
    """The root is the nearest folder above ``start`` with a ``.git``."""
    (repo / "src" / "pkg").mkdir(parents=True)
    assert sync.repo_root(repo / "src" / "pkg") == repo


def test_repo_root_of_a_worktree_is_the_worktree(repo: Path, tmp_path: Path) -> None:
    """A worktree's ``.git`` is a file, not a folder, and its root is the worktree, not the main repo."""
    git(repo, "-c", "user.name=A Developer", "-c", "user.email=dev@example.com", "commit", "--quiet", "--allow-empty", "--no-gpg-sign", "-m", "first")
    worktree: Path = tmp_path / "worktree"
    git(repo, "worktree", "add", "--quiet", str(worktree))
    assert (worktree / ".git").is_file()
    assert sync.repo_root(worktree) == worktree


def test_repo_root_needs_a_git_repo(tmp_path: Path) -> None:
    """Outside any git repo, there's no root."""
    with pytest.raises(sync.SyncError, match="not in a git repo"):
        sync.repo_root(tmp_path)


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
    """A missing, malformed or unknown pack list, or one without core, is an error."""
    text: str = PYPROJECT.replace('packs = ["core"]', "" if packs is None else f"packs = {packs}")
    (repo / "pyproject.toml").write_text(text)
    with pytest.raises(sync.SyncError, match=message.replace("[", r"\[").replace("(", r"\(").replace(")", r"\)")):
        sync.read_packs(repo)


def test_read_packs_puts_packs_in_order(repo: Path) -> None:
    """Packs come back in PACKS order, whatever order the repo lists them in."""
    (repo / "pyproject.toml").write_text(PYPROJECT.replace('["core"]', '["website", "core", "python"]'))
    assert sync.read_packs(repo) == ("core", "python", "website")


def test_read_packs_needs_a_pyproject(tmp_path: Path) -> None:
    """A repo with no pyproject.toml is an error."""
    with pytest.raises(sync.SyncError, match=r"no pyproject.toml"):
        sync.read_packs(tmp_path)


# --- what core owns


def test_core_owns_its_files() -> None:
    """The core pack writes exactly these files, its docs, its .gitignore block and its pyproject.toml keys."""
    want: sync.Expected = sync.expected(("core",))
    assert set(want.files) == {
        ".claude/settings.json",
        ".claude/skills/jetstream-new-feature/SKILL.md",
        ".claude/skills/jetstream-patch-vuln/SKILL.md",
        ".claude/skills/jetstream-ship/SKILL.md",
        ".github/dependabot.yml",
        ".github/workflows/jetstream-lint.yaml",
        ".github/workflows/jetstream-nightly-sca.yaml",
        ".jetstream/trivyignore",
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
    } | {f".jetstream/docs/core/{doc.name}" for doc in (ROOT / "src" / "jetstream" / "docs" / "core").glob("*.md")}
    assert ".jetstream/docs/core/markdown.md" in want.files
    assert want.files["cfg4dev.sh"].executable
    assert want.files[".jetstream/docs/core/markdown.md"].content.decode().startswith(sync.DOC_HEADER + "# Markdown")
    assert "entry: jetstream check" in want.files[".pre-commit-config.yaml"].content.decode()
    assert want.gitignore_block.startswith(sync.GITIGNORE_START + "\n")
    assert want.gitignore_block.endswith(sync.GITIGNORE_END + "\n")
    assert want.pyproject_keys[("tool", "uv", "exclude-newer")] == "7 days"


# --- what the python pack adds


def test_python_pack_adds_its_hooks_docs_and_keys() -> None:
    """The python pack's hooks join core's list as valid YAML, and its docs and keys are added to core's."""
    want: sync.Expected = sync.expected(("core", "python"))
    config: dict[str, Any] = yaml.safe_load(want.files[".pre-commit-config.yaml"].content)
    hook_ids: list[str] = [hook["id"] for hook in config["repos"][0]["hooks"]]
    assert hook_ids[0] == "jetstream-check"  # core's hooks come first, in the same list
    assert hook_ids[-7:] == ["ruff", "ty", "bandit", "deptry", "pyscn", "pip-audit", "licensecheck"]
    text: str = want.files[".pre-commit-config.yaml"].content.decode()
    assert text.count("repos:") == 1  # only what follows the python part's marker is appended
    assert sync.PART_MARKER not in text
    assert ".jetstream/docs/python/python.md" in want.files
    assert ".jetstream/pip-audit-ignore" in want.files
    nightly: dict[str, Any] = yaml.safe_load(want.files[".github/workflows/jetstream-nightly-sca.yaml"].content)
    assert [step["name"] for step in nightly["jobs"]["sca"]["steps"]][-2:] == ["trivy", "pip-audit"]
    assert want.pyproject_keys[("tool", "ruff", "lint", "select")] == ["ALL"]
    assert want.pyproject_keys[("tool", "uv", "exclude-newer")] == "7 days"  # core's keys too


# --- sync, then check


def test_sync_writes_everything_and_check_then_passes(repo: Path) -> None:
    """After sync, check passes and a second sync changes nothing."""
    assert sync.check(repo) != []
    changed: list[str] = sync.sync(repo)
    assert ".pre-commit-config.yaml" in changed
    assert ".gitignore" in changed
    assert "pyproject.toml" in changed
    assert sync.check(repo) == []
    assert sync.sync(repo) == []  # nothing left to change


def test_sync_adds_missing_keys_and_keeps_the_repos(repo: Path) -> None:
    """Syncing adds jetstream's keys after the repo's, without touching the repo's keys or comments."""
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
    """A changed jetstream key is named with both values, and sync puts back only that key."""
    pyproject: Path = synced / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace('exclude-newer = "7 days"', 'exclude-newer = "1 day"  # faster'))
    assert sync.check(synced) == ['pyproject.toml: [tool.uv] exclude-newer is "1 day"; jetstream sets "7 days"']

    assert sync.sync(synced) == ["pyproject.toml"]
    assert pyproject_of(synced)["tool"]["uv"]["exclude-newer"] == "7 days"
    assert sync.check(synced) == []


def test_a_repo_can_add_keys_to_jetstreams_tables(synced: Path) -> None:
    """A key the repo adds to one of jetstream's tables isn't a difference."""
    pyproject: Path = synced / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace("[tool.uv]\n", '[tool.uv]\ncache-keys = [{file = "x"}]\n'))
    assert sync.check(synced) == []
    assert sync.sync(synced) == []


def test_check_names_a_missing_key(synced: Path) -> None:
    """A deleted jetstream key is named with the value jetstream sets."""
    pyproject: Path = synced / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace('required-version = ">=0.13.5"\n', ""))
    assert sync.check(synced) == ['pyproject.toml: [tool.uv] required-version is missing; jetstream sets ">=0.13.5"']


def test_check_names_changed_missing_and_non_executable_files(synced: Path) -> None:
    """Each kind of difference in an owned file is named, and syncing fixes each."""
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
    """A jetstream-*.yaml workflow the release doesn't write is deleted; the repo's own workflows are kept."""
    workflows: Path = synced / ".github" / "workflows"  # sync wrote jetstream-lint.yaml there
    (workflows / "jetstream-old.yaml").write_text("old\n")
    (workflows / "deploy.yaml").write_text("the repo's own\n")
    assert sync.check(synced) == [".github/workflows/jetstream-old.yaml isn't written by this jetstream release"]

    assert sync.sync(synced) == [".github/workflows/jetstream-old.yaml (deleted)"]
    assert not (workflows / "jetstream-old.yaml").exists()
    assert (workflows / "deploy.yaml").exists()


def test_sync_deletes_jetstream_skills_the_release_does_not_write(synced: Path) -> None:
    """A jetstream-* skill the release doesn't write is deleted, folders and all; the repo's own skills are kept."""
    skills: Path = synced / ".claude" / "skills"  # sync wrote jetstream-ship there
    (skills / "jetstream-old" / "references").mkdir(parents=True)
    (skills / "jetstream-old" / "SKILL.md").write_text("old\n")
    (skills / "jetstream-old" / "references" / "notes.md").write_text("old\n")
    (skills / "deploy").mkdir()
    (skills / "deploy" / "SKILL.md").write_text("the repo's own\n")
    assert sync.check(synced) == [
        ".claude/skills/jetstream-old/SKILL.md isn't written by this jetstream release",
        ".claude/skills/jetstream-old/references/notes.md isn't written by this jetstream release",
    ]

    assert sync.sync(synced) == [
        ".claude/skills/jetstream-old/SKILL.md (deleted)",
        ".claude/skills/jetstream-old/references/notes.md (deleted)",
    ]
    assert not (skills / "jetstream-old").exists()
    assert (skills / "deploy" / "SKILL.md").exists()
    assert (skills / "jetstream-ship" / "SKILL.md").exists()
    assert sync.check(synced) == []


def test_sync_replaces_the_docs_as_a_whole(synced: Path) -> None:
    """Syncing rewrites an edited doc, and deletes any doc or pack folder the release doesn't write."""
    docs: Path = synced / ".jetstream" / "docs"
    (docs / "core" / "markdown.md").write_text("edited\n")
    (docs / "core" / "old.md").write_text("# Old\n")
    (docs / "retired").mkdir()
    (docs / "retired" / "gone.md").write_text("# Gone\n")
    assert sync.check(synced) == [
        ".jetstream/docs/core/markdown.md differs from what jetstream writes",
        ".jetstream/docs/core/old.md isn't written by this jetstream release",
        ".jetstream/docs/retired/gone.md isn't written by this jetstream release",
    ]

    assert sync.sync(synced) == [
        ".jetstream/docs/core/markdown.md",
        ".jetstream/docs/core/old.md (deleted)",
        ".jetstream/docs/retired/gone.md (deleted)",
    ]
    assert not (docs / "core" / "old.md").exists()
    assert not (docs / "retired").exists()
    assert sync.check(synced) == []


# --- .gitignore


def test_sync_puts_the_block_first_and_keeps_the_repos_lines(repo: Path) -> None:
    """In a .gitignore with no block, sync puts the block first, then the repo's lines."""
    (repo / ".gitignore").write_text("/output/\n")
    sync.sync(repo)
    text: str = (repo / ".gitignore").read_text()
    assert text == sync.expected(("core",)).gitignore_block + "\n/output/\n"


def test_sync_replaces_only_the_block(synced: Path) -> None:
    """A changed block is replaced, and the repo's lines either side are kept."""
    gitignore: Path = synced / ".gitignore"
    block: str = gitignore.read_text()
    gitignore.write_text("/before/\n" + block.replace(".venv/\n", "") + "/after/\n")
    assert sync.check(synced) == [".gitignore's jetstream block differs from what jetstream writes"]

    sync.sync(synced)
    assert gitignore.read_text() == "/before/\n" + block + "/after/\n"


def test_check_needs_the_block(synced: Path) -> None:
    """A .gitignore without jetstream's block is a difference."""
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
    """Markers that aren't one start line followed by one end line are an error, not a guess."""
    (synced / ".gitignore").write_text(text)
    with pytest.raises(sync.SyncError, match="exactly one"):
        sync.sync(synced)


# --- the command


def test_check_command_names_each_difference(synced: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """``jetstream check`` prints each difference and says to run sync, with its own exit status."""
    monkeypatch.chdir(synced)
    (synced / "mado.toml").write_text("changed\n")
    assert cli.main(["check"]) == cli.EXIT_DIFFERENT
    err: str = capsys.readouterr().err
    assert "*** jetstream: mado.toml differs from what jetstream writes\n" in err
    assert "run `jetstream sync`" in err


def test_sync_command_says_what_it_wrote(synced: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """``jetstream sync`` prints each file it wrote, and check then passes."""
    monkeypatch.chdir(synced / ".")
    (synced / "mado.toml").unlink()
    assert cli.main(["sync"]) == cli.EXIT_OK
    assert capsys.readouterr().out == "jetstream sync: wrote mado.toml\n"
    assert cli.main(["check"]) == cli.EXIT_OK


def test_commands_report_setup_errors_in_one_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Outside a git repo, a command fails with one ``*** jetstream:`` line, not a traceback."""
    monkeypatch.chdir(tmp_path)
    assert cli.main(["check"]) == cli.EXIT_ERROR
    assert capsys.readouterr().err == "*** jetstream: not in a git repo\n"


def test_jetstream_passes_its_own_check() -> None:
    """The jetstream repo itself is what its own sync writes."""
    assert sync.check(ROOT) == [], "run jetstream sync"
