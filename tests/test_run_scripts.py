"""Tests for the core pack's run-*.sh scripts, each run in a throwaway git repo.

The scripts are run from this .venv/bin, with a PATH that doesn't include it,
to check that each one finds the tools installed next to it.
"""

import functools
import shutil
import subprocess
import sys
from pathlib import Path
from collections.abc import Callable
from typing import Final

import pytest

ROOT: Final[Path] = Path(__file__).parent.parent
VENV_BIN: Final[Path] = Path(sys.prefix) / "bin"
CORE_FILES: Final[Path] = ROOT / "src" / "jetstream" / "files" / "core"
AUTHOR: Final[str] = "A Developer <dev@example.com>"
# run(repo, "run-<tool>.sh", *args) runs a script in repo.
type Run = Callable[..., subprocess.CompletedProcess[str]]

# The system commands the scripts may use. Tests run the scripts with only
# these on PATH, so a tool installed on this machine can't stand in for the
# one jetstream installs.
SYSTEM_COMMANDS: Final[tuple[str, ...]] = (
    "bash", "basename", "cat", "cmp", "dirname", "env", "git", "grep", "mktemp", "rm", "sed",
)  # fmt: skip


def git(repo: Path, *args: str) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


@pytest.fixture(scope="session")
def system_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    """A PATH with only links to SYSTEM_COMMANDS."""
    bin_dir: Path = tmp_path_factory.mktemp("system-bin")
    for command in SYSTEM_COMMANDS:
        found: str | None = shutil.which(command)
        assert found is not None, command
        (bin_dir / command).symlink_to(found)
    return str(bin_dir)


@pytest.fixture
def run(system_path: str) -> Run:
    return functools.partial(run_script, system_path)


def run_script(system_path: str, repo: Path, script: str, *args: str) -> subprocess.CompletedProcess[str]:
    env: dict[str, str] = {
        "PATH": system_path,
        "HOME": str(repo.parent),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return subprocess.run(
        [str(VENV_BIN / script), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )


def add(repo: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path: Path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    git(repo, "add", "--", *files)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo on branch ``work`` with the core pack's owned config files."""
    repo: Path = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet", "--initial-branch=work")
    git(repo, "config", "user.name", "A Developer")
    git(repo, "config", "user.email", "dev@example.com")
    git(repo, "config", "commit.gpgsign", "false")
    for owned in CORE_FILES.iterdir():
        if owned.is_file():  # the config files, not the workflow, which would change what zizmor sees
            shutil.copy(owned, repo / owned.name)
    git(repo, "add", ".")
    return repo


# --- yamllint


def test_yamllint_passes_good_yaml(repo: Path, run: Run) -> None:
    add(repo, {"a.yaml": "---\nkey: value\n"})
    assert run(repo, "run-yamllint.sh").returncode == 0


def test_yamllint_fails_bad_yaml(repo: Path, run: Run) -> None:
    add(repo, {"a.yml": "---\nkey: value\nkey: again\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-yamllint.sh")
    assert result.returncode != 0
    assert "duplication of key" in result.stdout


# --- json-lint


def test_json_lint_passes_jq_formatted_json(repo: Path, run: Run) -> None:
    add(repo, {"a.json": '{\n  "key": [\n    1,\n    2\n  ]\n}\n'})
    assert run(repo, "run-json-lint.sh").returncode == 0


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ('{"key": [1, 2]}\n', "Unformatted JSON: a.json"),
        ('{\n  "key": 1\n}', "Unformatted JSON: a.json"),  # no final newline
        ('{"key": }\n', "Invalid JSON: a.json"),
    ],
)
def test_json_lint_fails(repo: Path, run: Run, content: str, message: str) -> None:
    add(repo, {"a.json": content})
    result: subprocess.CompletedProcess[str] = run(repo, "run-json-lint.sh")
    assert result.returncode == 1
    assert message in result.stderr


def test_json_lint_skips_jsonlintignore_patterns(repo: Path, run: Run) -> None:
    add(repo, {".vscode/settings.json": '{\n  // a comment\n  "key": 1,\n}\n'})
    assert run(repo, "run-json-lint.sh").returncode == 0


# --- mado


def test_mado_passes_good_markdown(repo: Path, run: Run) -> None:
    add(repo, {"README.md": "# Title\n\nSome text.\n"})
    assert run(repo, "run-mado.sh").returncode == 0


def test_mado_fails_bad_markdown(repo: Path, run: Run) -> None:
    add(repo, {"README.md": "# Title\n\n#Not a heading\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-mado.sh")
    assert result.returncode != 0
    assert "MD018" in result.stdout + result.stderr


# --- shellcheck


def test_shellcheck_fails_unquoted_variable(repo: Path, run: Run) -> None:
    add(repo, {"a.sh": '#!/usr/bin/env bash\necho $1\n', "b.sh": '#!/usr/bin/env bash\necho "$1"\n'})
    result: subprocess.CompletedProcess[str] = run(repo, "run-shellcheck.sh")
    assert result.returncode != 0
    assert "In a.sh line 2" in result.stdout
    assert "b.sh" not in result.stdout


def test_shellcheck_passes_with_no_shell_scripts(repo: Path, run: Run) -> None:
    assert run(repo, "run-shellcheck.sh").returncode == 0


# --- zizmor


def test_zizmor_passes_with_no_workflows(repo: Path, run: Run) -> None:
    assert run(repo, "run-zizmor.sh").returncode == 0


def test_zizmor_fails_an_unpinned_action(repo: Path, run: Run) -> None:
    add(
        repo,
        {
            ".github/workflows/ci.yaml": (
                "---\nname: ci\non: push\npermissions: {}\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
                "    steps:\n      - uses: actions/checkout@v5\n"
            ),
        },
    )
    result: subprocess.CompletedProcess[str] = run(repo, "run-zizmor.sh")
    assert result.returncode != 0
    assert "unpinned" in result.stdout


def test_zizmor_rejects_an_unknown_persona(repo: Path, run: Run) -> None:
    assert run(repo, "run-zizmor.sh", "--persona", "nope").returncode == 1


# --- gitleaks


def test_gitleaks_passes_a_clean_history(repo: Path, run: Run) -> None:
    add(repo, {"a.txt": "nothing secret\n"})
    git(repo, "commit", "--quiet", "-m", "clean")
    assert run(repo, "run-gitleaks.sh").returncode == 0


def test_gitleaks_finds_a_committed_secret(repo: Path, run: Run) -> None:
    add(repo, {"config.txt": 'github_token = "ghp_' + "Z3x9Qm2LkP7vR4tY8wN1bC6dF0hJ5sA2eG7u" + '"\n'})
    git(repo, "commit", "--quiet", "-m", "oops")
    result: subprocess.CompletedProcess[str] = run(repo, "run-gitleaks.sh")
    assert result.returncode != 0
    assert "leaks found" in result.stdout + result.stderr


# --- unit-tests


def test_unit_tests_pass_when_there_are_no_tests(repo: Path, run: Run) -> None:
    assert run(repo, "run-unit-tests.sh").returncode == 0


def test_unit_tests_fail_a_failing_test_but_skip_integration_tests(repo: Path, run: Run) -> None:
    add(
        repo,
        {
            "pyproject.toml": '[tool.pytest.ini_options]\nmarkers = ["integration: slow"]\n',
            "tests/test_a.py": (
                "import pytest\n\n\ndef test_fails():\n    assert False\n\n\n"
                "@pytest.mark.integration\ndef test_integration():\n    assert False\n"
            ),
        },
    )
    result: subprocess.CompletedProcess[str] = run(repo, "run-unit-tests.sh")
    assert result.returncode == 1
    assert "1 failed, 1 deselected" in result.stdout


# --- d2-compile and check-svg


def test_check_svg_passes_a_compiled_diagram_and_fails_a_stale_one(repo: Path, run: Run) -> None:
    add(repo, {"docs/images/d2/flow.d2": "a -> b\n"})
    assert run(repo, "run-d2-compile.sh").returncode == 0
    git(repo, "add", ".")
    assert run(repo, "run-check-svg.sh").returncode == 0

    add(repo, {"docs/images/d2/flow.d2": "a -> c\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-check-svg.sh")
    assert result.returncode == 1
    assert "Stale SVG: docs/images/flow.svg" in result.stderr


def test_check_svg_fails_an_svg_without_a_source(repo: Path, run: Run) -> None:
    add(repo, {"docs/images/orphan.svg": '<svg xmlns="http://www.w3.org/2000/svg"/>\n', "logo.svg": "<svg/>\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-check-svg.sh")
    assert result.returncode == 1
    assert "Missing source: docs/images/orphan.svg" in result.stderr
    assert "logo.svg" not in result.stderr


def test_d2_compile_fails_a_source_outside_images_d2(repo: Path, run: Run) -> None:
    add(repo, {"docs/flow.d2": "a -> b\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-d2-compile.sh")
    assert result.returncode == 1
    assert "outside an images/d2 directory: docs/flow.d2" in result.stderr


# --- dco


def test_dco_passes_a_signed_off_message(repo: Path, tmp_path: Path, run: Run) -> None:
    message: Path = tmp_path / "COMMIT_EDITMSG"
    message.write_text(f"feat: a change\n\nSigned-off-by: {AUTHOR}\n")
    assert run(repo, "run-dco.sh", str(message)).returncode == 0


@pytest.mark.parametrize(
    "trailer",
    ["", "Signed-off-by: Someone Else <else@example.com>\n", f"Signed-off-by: {AUTHOR} extra\n"],
)
def test_dco_fails_without_the_authors_sign_off(repo: Path, tmp_path: Path, run: Run, trailer: str) -> None:
    message: Path = tmp_path / "COMMIT_EDITMSG"
    message.write_text(f"feat: a change\n\n{trailer}")
    result: subprocess.CompletedProcess[str] = run(repo, "run-dco.sh", str(message))
    assert result.returncode == 1
    assert f"'Signed-off-by: {AUTHOR}'" in result.stderr


def commit(repo: Path, subject: str, *, signed: bool, author: str = AUTHOR) -> None:
    body: str = f"{subject}\n\nSigned-off-by: {author}\n" if signed else f"{subject}\n"
    git(repo, "commit", "--quiet", "--allow-empty", f"--author={author}", "-m", body)


def test_dco_commits_passes_when_every_commit_is_signed_off(repo: Path, run: Run) -> None:
    commit(repo, "base", signed=False)
    base: str = git(repo, "rev-parse", "HEAD").strip()
    commit(repo, "one", signed=True)
    commit(repo, "two by someone else", signed=True, author="Other Person <other@example.com>")
    assert run(repo, "run-dco.sh", "--commits", f"{base}..HEAD").returncode == 0


def test_dco_commits_names_each_unsigned_commit(repo: Path, run: Run) -> None:
    commit(repo, "base", signed=False)
    base: str = git(repo, "rev-parse", "HEAD").strip()
    commit(repo, "signed", signed=True)
    commit(repo, "unsigned", signed=False)
    git(repo, "commit", "--quiet", "--allow-empty", "--author=Other Person <other@example.com>", "-m", f"wrong signer\n\nSigned-off-by: {AUTHOR}\n")
    result: subprocess.CompletedProcess[str] = run(repo, "run-dco.sh", "--commits", f"{base}..HEAD")
    assert result.returncode == 1
    assert " unsigned: no 'Signed-off-by: A Developer <dev@example.com>'" in result.stderr
    assert " wrong signer: no 'Signed-off-by: Other Person <other@example.com>'" in result.stderr
    assert " signed:" not in result.stderr
    assert "2 commit(s) without a DCO sign-off" in result.stderr


@pytest.mark.parametrize("args", [[], ["--commits"], ["a", "b"]])
def test_dco_usage(repo: Path, run: Run, args: list[str]) -> None:
    result: subprocess.CompletedProcess[str] = run(repo, "run-dco.sh", *args)
    assert result.returncode == 1
    assert "usage:" in result.stderr


# --- no-commit-to-branch


def test_no_commit_to_branch(repo: Path, run: Run) -> None:
    git(repo, "commit", "--quiet", "-m", "first")
    assert run(repo, "run-no-commit-to-branch.sh").returncode == 0  # on work

    git(repo, "checkout", "--quiet", "-b", "main")
    result: subprocess.CompletedProcess[str] = run(repo, "run-no-commit-to-branch.sh")
    assert result.returncode == 1
    assert "Don't commit directly to main" in result.stderr
    assert run(repo, "run-no-commit-to-branch.sh", "release").returncode == 0

    git(repo, "checkout", "--quiet", "--detach")
    assert run(repo, "run-no-commit-to-branch.sh").returncode == 0
