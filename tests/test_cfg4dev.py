"""Tests for how ``cfg4dev.sh`` installs a site's npm packages, with stubs for the tools it runs."""

import os
import subprocess
from pathlib import Path
from typing import Final

import pytest

CFG4DEV: Final[Path] = Path(__file__).resolve().parent.parent / "src" / "jetstream" / "files" / "core" / "cfg4dev.sh"
LOCK: Final[str] = "install --package-lock-only"

# npm, recording each call; locking writes package-lock.json, unless the test has it fail
NPM: Final[str] = """#!/bin/bash
echo "$*" >> npm-calls
if [[ "$1" == install ]]; then
    [[ -z "${NPM_FAILS:-}" ]] || exit 1
    touch package-lock.json
fi
"""


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
    repo: Path = tmp_path / "repo"
    stubs: Path = tmp_path / "stubs"
    repo.mkdir()
    stubs.mkdir()
    for name, text in {"uv": "#!/bin/bash\n", "jetstream": "#!/bin/bash\n", "pre-commit": "#!/bin/bash\n", "node": "#!/bin/bash\necho v26.0.0\n", "npm": NPM}.items():
        (stubs / name).write_text(text)
        (stubs / name).chmod(0o755)
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)  # noqa: S607 (git, wherever it is)
    (repo / "pyproject.toml").touch()
    for name in files:
        (repo / name).write_text("26\n" if name == ".nvmrc" else "{}\n")
    env: dict[str, str] = {"PATH": f"{stubs}:{os.environ['PATH']}", "HOME": str(tmp_path), "VIRTUAL_ENV": str(repo / ".venv")}  # as if its .venv is active
    if npm_fails:
        env["NPM_FAILS"] = "1"
    subprocess.run(["bash", "-c", f"source {CFG4DEV}"], cwd=repo, env=env, check=False)  # noqa: S603, S607 (only the test's own arguments)
    recorded: Path = repo / "npm-calls"
    assert (recorded.read_text().splitlines() if recorded.exists() else []) == calls
