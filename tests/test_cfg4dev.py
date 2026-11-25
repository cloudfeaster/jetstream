"""Tests for ``cfg4dev.sh``, with stubs for the tools it runs, and for ``terminal-init.sh``, with a stub for ``cfg4dev.sh``."""

import os
import subprocess
from pathlib import Path
from typing import Final

import pytest

CFG4DEV: Final[Path] = Path(__file__).resolve().parent.parent / "src" / "jetstream" / "files" / "core" / "cfg4dev.sh"
TERMINAL_INIT: Final[Path] = CFG4DEV.parent / ".vscode" / "terminal-init.sh"
LOCK: Final[str] = "install --package-lock-only"

# npm, recording each call; locking writes package-lock.json, unless the test has it fail
NPM: Final[str] = """echo "$*" >> npm-calls
if [[ "$1" == install ]]; then
    [[ -z "${NPM_FAILS:-}" ]] || exit 1
    touch package-lock.json
fi
"""


def make_repo(tmp_path: Path, files: list[str]) -> Path:
    """Return a new repo with ``files`` in it."""
    repo: Path = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)  # noqa: S607 (git, wherever it is)
    (repo / "pyproject.toml").touch()
    for name in files:
        (repo / name).write_text("26\n" if name == ".nvmrc" else "{}\n")
    return repo


def make_env(tmp_path: Path, scripts: dict[str, str]) -> dict[str, str]:
    """Return an environment with a stub for each tool cfg4dev.sh runs, which does nothing unless it's in ``scripts``."""
    stubs: Path = tmp_path / "stubs"
    stubs.mkdir()
    for name, text in ({"uv": "", "jetstream": "", "pre-commit": "", "npm": "", "node": "echo v26.0.0"} | scripts).items():
        (stubs / name).write_text(f"#!/bin/bash\n{text}\n")
        (stubs / name).chmod(0o755)
    return {"PATH": f"{stubs}:{os.environ['PATH']}", "HOME": str(tmp_path), "VIRTUAL_ENV": str(tmp_path / "repo" / ".venv")}  # as if its .venv is active


@pytest.mark.parametrize(
    ("files", "npm_fails", "calls"),
    [
        pytest.param([".nvmrc", "package.json"], False, [LOCK, "ci"], id="a-new-site-is-locked-then-installed"),
        pytest.param([".nvmrc", "package.json", "package-lock.json"], False, ["ci"], id="a-lockfile-is-kept"),
        pytest.param([".nvmrc", "package.json"], True, [LOCK], id="nothing-is-installed-if-locking-fails"),
        pytest.param([".nvmrc"], False, [], id="no-package-json"),
        pytest.param(["package.json"], False, [], id="no-website-pack"),
    ],
)
def test_cfg4dev_locks_and_installs_npm_packages(tmp_path: Path, files: list[str], calls: list[str], *, npm_fails: bool) -> None:
    """A site with no package-lock.json gets one, and one that has it keeps it."""
    repo: Path = make_repo(tmp_path, files)
    env: dict[str, str] = make_env(tmp_path, {"npm": NPM})
    if npm_fails:
        env["NPM_FAILS"] = "1"
    subprocess.run(["bash", "-c", f"source {CFG4DEV}"], cwd=repo, env=env, check=False)  # noqa: S603, S607 (only the test's own arguments)
    recorded: Path = repo / "npm-calls"
    assert (recorded.read_text().splitlines() if recorded.exists() else []) == calls


@pytest.mark.parametrize(
    ("stubs", "local", "status", "hooks_installed"),
    [
        pytest.param({}, "true", 0, True, id="nothing-fails"),
        pytest.param({"uv": '[[ "$1" != self ]]'}, "true", 0, True, id="uv-self-update"),
        pytest.param({"uv": '[[ "$1" != sync ]]'}, "true", 1, False, id="uv-sync"),
        pytest.param({"jetstream": "exit 1"}, "true", 1, True, id="jetstream-sync"),
        pytest.param({"jetstream": "echo >> pyproject.toml", "uv": '[[ "$1" != sync || ! -s pyproject.toml ]]'}, "true", 1, True, id="uv-sync-after-jetstream-sync"),
        pytest.param({"npm": '[[ "$1" != install ]]'}, "true", 1, True, id="npm-install"),
        pytest.param({"npm": '[[ "$1" != ci ]] && touch package-lock.json'}, "true", 1, True, id="npm-ci"),
        pytest.param({"pre-commit": "touch hooks-installed; exit 1"}, "true", 1, True, id="pre-commit-install"),
        pytest.param({}, "false", 1, True, id="cfg4dev-local"),
        pytest.param({"jetstream": "exit 1", "npm": "exit 1"}, "true", 1, True, id="two-steps"),
    ],
)
def test_cfg4dev_fails_if_a_step_fails(tmp_path: Path, stubs: dict[str, str], local: str, status: int, *, hooks_installed: bool) -> None:
    """A failed step makes the status 1, but the later steps still run, and the shell is left in the directory it was in."""
    repo: Path = make_repo(tmp_path, [".nvmrc", "package.json"])
    (repo / "cfg4dev.local.sh").write_text(f"touch local-ran\n{local}\n")
    subdir: Path = repo / "subdir"
    subdir.mkdir()
    env: dict[str, str] = make_env(tmp_path, {"pre-commit": "touch hooks-installed", "npm": "touch package-lock.json"} | stubs)
    done: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603 (only the test's own arguments)
        ["bash", "-c", f'source {CFG4DEV}; echo "$? ${{PWD}} ${{_jetstream_status-unset}}"'],  # noqa: S607 (bash, wherever it is)
        cwd=subdir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert done.stdout.splitlines()[-1] == f"{status} {subdir} unset"
    assert (repo / "hooks-installed").exists() == hooks_installed
    assert (repo / "local-ran").exists() == hooks_installed


@pytest.mark.parametrize(
    ("status", "out", "err"),
    [
        pytest.param(0, "dev terminal has been initialized by terminal-init.sh!\n", "", id="set-up"),
        pytest.param(1, "", "*** dev terminal setup failed: see above\n", id="failed"),
    ],
)
def test_terminal_init_says_whether_setup_worked(tmp_path: Path, status: int, out: str, err: str) -> None:
    """A new terminal says it's set up only if cfg4dev.sh succeeded."""
    script: Path = tmp_path / ".vscode" / "terminal-init.sh"
    script.parent.mkdir()
    script.write_text(TERMINAL_INIT.read_text())
    (tmp_path / "cfg4dev.sh").write_text(f"return {status}\n")
    done: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603 (only the test's own arguments)
        ["bash", "-c", f"source {script}"],  # noqa: S607 (bash, wherever it is)
        env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), "OSTYPE": "linux-gnu"},  # (on macOS it would hand off to zsh)
        check=True,
        capture_output=True,
        text=True,
    )
    assert (done.stdout, done.stderr) == (out, err)
