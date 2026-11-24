"""The pack matrix: a new repo, for every combination of packs, passes its own checks from the start.

Each case does what ``new-repo.md`` says to, with this working tree as the
jetstream release. A new repo pins jetstream's release tag on GitHub, so the
working tree is committed to a repo of its own and tagged as that release, and
git fetches that repo wherever it's asked for GitHub's. uv gets a cache of its
own, so the user's never holds this jetstream as the release.
"""

import itertools
import os
import shutil
import subprocess
import sys
import tomllib
from importlib.metadata import version
from pathlib import Path
from typing import Any, Final, NamedTuple

import pytest

from jetstream import new_repo, sync

pytestmark = pytest.mark.integration  # uv sync, and the hooks that use the network

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
URL: Final[str] = "https://github.com/cloudfeaster/jetstream"
TAG: Final[str] = f"v{version('cloudfeaster-jetstream')}"
OTHER_PACKS: Final[list[str]] = [pack for pack in sync.PACKS if pack != "core" and (new_repo.STARTERS / pack).is_dir()]
MATRIX: Final[list[tuple[str, ...]]] = [packs for size in range(len(OTHER_PACKS) + 1) for packs in itertools.combinations(OTHER_PACKS, size)]


class Release(NamedTuple):
    """The working tree, as a jetstream release: its commit, and the environment that uses it."""

    commit: str
    env: dict[str, str]


def run(cwd: Path, env: dict[str, str], *command: str) -> str:
    """Run a command, which must succeed, and return its output."""
    result: subprocess.CompletedProcess[str] = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False)  # noqa: S603 (only the test's own arguments)
    assert result.returncode == 0, f"{' '.join(command)}\n{result.stdout}{result.stderr}"
    return result.stdout


@pytest.fixture(scope="module")
def release(tmp_path_factory: pytest.TempPathFactory) -> Release:
    """Return the working tree, committed and tagged as the release a new repo pins."""
    tmp: Path = tmp_path_factory.mktemp("release")
    source: Path = tmp / "jetstream"
    gitconfig: Path = tmp / "gitconfig"
    gitconfig.write_text(f'[user]\n\tname = test\n\temail = test@example.org\n[url "{source.as_uri()}"]\n\tinsteadOf = {URL}\n')
    # Without the variables of any git command or .venv the tests run in, or that .venv's tools on PATH.
    env: dict[str, str] = {name: value for name, value in os.environ.items() if not name.startswith("GIT_") and name != "VIRTUAL_ENV"}
    env |= {
        "PATH": os.pathsep.join(path for path in env["PATH"].split(os.pathsep) if path != str(Path(sys.prefix) / "bin")),
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "UV_CACHE_DIR": str(tmp / "uv-cache"),
        "UV_NO_GITHUB_FAST_PATH": "1",  # uv would ask GitHub's API for the tag's commit, rather than git
    }
    for path in run(ROOT, env, "git", "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0"):
        if path and os.path.lexists(ROOT / path):  # a file deleted but still in the index isn't there
            (source / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, source / path, follow_symlinks=False)
    run(source, env, "git", "init", "--quiet")
    run(source, env, "git", "add", "--all")
    run(source, env, "git", "commit", "--quiet", "--message", "the working tree")
    run(source, env, "git", "tag", TAG)
    return Release(run(source, env, "git", "rev-parse", "HEAD").strip(), env)


@pytest.mark.parametrize("packs", MATRIX, ids=["+".join(("core", *packs)) for packs in MATRIX])
def test_a_new_repo_passes_its_checks(release: Release, tmp_path: Path, packs: tuple[str, ...]) -> None:
    """A new repo installs jetstream and its tools, and passes ``jetstream check`` and every hook."""
    repo: Path = tmp_path / "my-repo"
    repo.mkdir()
    run(repo, release.env, "git", "init", "--quiet", "--initial-branch", "main")
    run(repo, release.env, "git", "commit", "--quiet", "--allow-empty", "--message", "chore: start the repo")
    run(repo, release.env, "git", "switch", "--quiet", "--create", "feat/start-on-jetstream")
    run(repo, release.env, "uvx", "--from", f"git+{URL}@{TAG}", "jetstream", "new-repo", "--description", "A new repo", *(f"--pack={pack}" for pack in packs))
    run(repo, release.env, "uv", "sync")
    locked: list[dict[str, Any]] = tomllib.loads((repo / "uv.lock").read_text())["package"]
    assert next(package["source"] for package in locked if package["name"] == new_repo.DISTRIBUTION) == {"git": f"{URL}?tag={TAG}#{release.commit}"}  # this working tree
    run(repo, release.env, "uv", "run", "--no-sync", "jetstream", "check")
    run(repo, release.env, "git", "add", "--all")
    run(repo, release.env, "uv", "run", "--no-sync", "pre-commit", "run", "--all-files")
