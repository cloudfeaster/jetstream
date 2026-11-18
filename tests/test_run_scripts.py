"""Tests for the core pack's run-*.sh scripts, each run in a throwaway git repo.

The scripts are run from this .venv/bin, with a PATH that doesn't include it,
to check that each one finds the tools installed next to it.
"""

import functools
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final

import pytest

ROOT: Final[Path] = Path(__file__).parent.parent
VENV_BIN: Final[Path] = Path(sys.prefix) / "bin"
CORE_FILES: Final[Path] = ROOT / "src" / "jetstream" / "files" / "core"
CORE_PARTS: Final[Path] = ROOT / "src" / "jetstream" / "parts" / "core"
PYTHON_PARTS: Final[Path] = ROOT / "src" / "jetstream" / "parts" / "python"
# run(repo, "run-<tool>.sh", *args) runs a script in repo.
type Run = Callable[..., subprocess.CompletedProcess[str]]

# The system commands the scripts may use. Tests run the scripts with only
# these on PATH, so a tool installed on this machine can't stand in for the
# one jetstream installs.
SYSTEM_COMMANDS: Final[tuple[str, ...]] = (
    "bash", "basename", "cat", "cmp", "dirname", "env", "git", "grep", "mktemp", "rm", "sed",
)  # fmt: skip


def git(repo: Path, *args: str) -> str:
    """Run git in ``repo`` and return its output."""
    result: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603 (the tests' own arguments)
        ["git", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


@pytest.fixture(scope="session")
def system_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Return a PATH with only links to SYSTEM_COMMANDS."""
    bin_dir: Path = tmp_path_factory.mktemp("system-bin")
    for command in SYSTEM_COMMANDS:
        found: str | None = shutil.which(command)
        assert found is not None, command
        (bin_dir / command).symlink_to(found)
    return str(bin_dir)


@pytest.fixture
def run(system_path: str) -> Run:
    """Return ``run_script`` with this session's restricted PATH."""
    return functools.partial(run_script, system_path)


def run_script(system_path: str, repo: Path, script: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``.venv/bin/<script>`` in ``repo``, with only SYSTEM_COMMANDS on PATH and git's system config ignored."""
    env: dict[str, str] = {
        "PATH": system_path,
        "HOME": str(repo.parent),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return subprocess.run(  # noqa: S603 (the tests' own arguments)
        [str(VENV_BIN / script), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )


def add(repo: Path, files: dict[str, str]) -> None:
    """Write ``files`` into ``repo``, by path, and stage them."""
    for name, content in files.items():
        path: Path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    git(repo, "add", "--", *files)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Return a git repo on branch ``work`` with the core pack's owned config files."""
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
    """A valid YAML file passes jetstream's strict yamllint."""
    add(repo, {"a.yaml": "---\nkey: value\n"})
    assert run(repo, "run-yamllint.sh").returncode == 0


def test_yamllint_fails_bad_yaml(repo: Path, run: Run) -> None:
    """A duplicated key fails, for a *.yml file too."""
    add(repo, {"a.yml": "---\nkey: value\nkey: again\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-yamllint.sh")
    assert result.returncode != 0
    assert "duplication of key" in result.stdout


# --- json-lint


def test_json_lint_passes_jq_formatted_json(repo: Path, run: Run) -> None:
    """JSON formatted as jq formats it passes."""
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
    """Compact JSON, JSON with no final newline and invalid JSON each fail, naming the file."""
    add(repo, {"a.json": content})
    result: subprocess.CompletedProcess[str] = run(repo, "run-json-lint.sh")
    assert result.returncode == 1
    assert message in result.stderr


def test_json_lint_skips_jsonlintignore_patterns(repo: Path, run: Run) -> None:
    """A JSONC file under .vscode, skipped by .jsonlintignore, passes."""
    add(repo, {".vscode/settings.json": '{\n  // a comment\n  "key": 1,\n}\n'})
    assert run(repo, "run-json-lint.sh").returncode == 0


# --- mado


def test_mado_passes_good_markdown(repo: Path, run: Run) -> None:
    """Markdown that follows the mado.toml rules passes."""
    add(repo, {"README.md": "# Title\n\nSome text.\n"})
    assert run(repo, "run-mado.sh").returncode == 0


def test_mado_fails_bad_markdown(repo: Path, run: Run) -> None:
    """A heading with no space after the ``#`` fails MD018."""
    add(repo, {"README.md": "# Title\n\n#Not a heading\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-mado.sh")
    assert result.returncode != 0
    assert "MD018" in result.stdout + result.stderr


# --- shellcheck


def test_shellcheck_fails_unquoted_variable(repo: Path, run: Run) -> None:
    """An unquoted variable fails, and shellcheck reports only the script that has one."""
    add(repo, {"a.sh": "#!/usr/bin/env bash\necho $1\n", "b.sh": '#!/usr/bin/env bash\necho "$1"\n'})
    result: subprocess.CompletedProcess[str] = run(repo, "run-shellcheck.sh")
    assert result.returncode != 0
    assert "In a.sh line 2" in result.stdout
    assert "b.sh" not in result.stdout


def test_shellcheck_passes_with_no_shell_scripts(repo: Path, run: Run) -> None:
    """A repo with no *.sh files passes, rather than shellcheck failing with no arguments."""
    assert run(repo, "run-shellcheck.sh").returncode == 0


# --- sqlfluff

# jetstream's sqlfluff keys, plus the dialect, which each repo sets.
SQLFLUFF_PYPROJECT: Final[str] = (CORE_PARTS / "pyproject.toml").read_text().replace("[tool.sqlfluff.core]\n", '[tool.sqlfluff.core]\ndialect = "sqlite"\n')


def test_sqlfluff_passes_good_sql_and_templates(repo: Path, run: Run) -> None:
    """Upper-case SQL passes, in a plain file and in a Jinja template."""
    add(
        repo,
        {
            "pyproject.toml": SQLFLUFF_PYPROJECT,
            "a.sql": "SELECT a FROM t\n",
            "b.sql.j2": "SELECT a FROM t\n{% if true %}WHERE a = 1{% endif %}\n",
        },
    )
    result: subprocess.CompletedProcess[str] = run(repo, "run-sqlfluff.sh")
    assert result.returncode == 0, result.stdout + result.stderr


def test_sqlfluff_fails_with_jetstreams_rules(repo: Path, run: Run) -> None:
    """Lower-case keywords fail jetstream's capitalisation rule, and only that file is reported."""
    add(repo, {"pyproject.toml": SQLFLUFF_PYPROJECT, "a.sql": "select a from t\n", "b.sql": "SELECT a FROM t\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-sqlfluff.sh")
    assert result.returncode != 0
    assert "== [a.sql] FAIL" in result.stdout
    assert "CP01" in result.stdout  # jetstream's upper-case keywords
    assert "b.sql" not in result.stdout


def test_sqlfluff_passes_with_no_sql(repo: Path, run: Run) -> None:
    """A repo with no SQL files passes."""
    assert run(repo, "run-sqlfluff.sh").returncode == 0


# --- ruff and ty


# jetstream's ruff keys, as the python pack writes them into a repo's pyproject.toml.
PYTHON_PYPROJECT: Final[str] = (PYTHON_PARTS / "pyproject.toml").read_text()
GOOD_PYTHON: Final[str] = '"""A module."""\n\nANSWER: int = 42\n'


def test_ruff_passes_good_python(repo: Path, run: Run) -> None:
    """A module that meets every rule jetstream selects passes."""
    add(repo, {"pyproject.toml": PYTHON_PYPROJECT, "a.py": GOOD_PYTHON})
    result: subprocess.CompletedProcess[str] = run(repo, "run-ruff.sh")
    assert result.returncode == 0, result.stdout + result.stderr


def test_ruff_fails_a_lint_finding(repo: Path, run: Run) -> None:
    """An unused import fails ruff check."""
    add(repo, {"pyproject.toml": PYTHON_PYPROJECT, "a.py": '"""A module."""\n\nimport os\n'})
    result: subprocess.CompletedProcess[str] = run(repo, "run-ruff.sh")
    assert result.returncode != 0
    assert "F401" in result.stdout


def test_ruff_fails_unformatted_python_without_changing_it(repo: Path, run: Run) -> None:
    """Unformatted code fails ruff format's check, and the file is left as it was."""
    unformatted: str = GOOD_PYTHON.replace("ANSWER: int = 42", "ANSWER: int=42")
    add(repo, {"pyproject.toml": PYTHON_PYPROJECT, "a.py": unformatted})
    result: subprocess.CompletedProcess[str] = run(repo, "run-ruff.sh")
    assert result.returncode != 0
    assert "1 file would be reformatted" in result.stdout
    assert (repo / "a.py").read_text() == unformatted


def test_ruff_skips_the_repos_excludes(repo: Path, run: Run) -> None:
    """A file in the repo's [tool.ruff] exclude isn't checked, though the script names it."""
    pyproject: str = PYTHON_PYPROJECT.replace("[tool.ruff]\n", '[tool.ruff]\nexclude = ["generated"]\n')
    add(repo, {"pyproject.toml": pyproject, "a.py": GOOD_PYTHON, "generated/b.py": "import os\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-ruff.sh")
    assert result.returncode == 0, result.stdout + result.stderr


def test_ruff_passes_with_no_python(repo: Path, run: Run) -> None:
    """A repo with no *.py files passes."""
    assert run(repo, "run-ruff.sh").returncode == 0


def test_ty_passes_good_python(repo: Path, run: Run) -> None:
    """Correctly typed code passes."""
    add(repo, {"pyproject.toml": PYTHON_PYPROJECT, "a.py": GOOD_PYTHON})
    result: subprocess.CompletedProcess[str] = run(repo, "run-ty.sh")
    assert result.returncode == 0, result.stdout + result.stderr


def test_ty_fails_a_type_error(repo: Path, run: Run) -> None:
    """Assigning a str to a variable annotated int fails."""
    add(repo, {"pyproject.toml": PYTHON_PYPROJECT, "a.py": GOOD_PYTHON.replace("42", '"42"')})
    result: subprocess.CompletedProcess[str] = run(repo, "run-ty.sh")
    assert result.returncode != 0
    assert "invalid-assignment" in result.stdout


def test_ty_passes_with_no_python(repo: Path, run: Run) -> None:
    """A repo with no *.py files passes."""
    assert run(repo, "run-ty.sh").returncode == 0


# --- zizmor


def test_zizmor_passes_with_no_workflows(repo: Path, run: Run) -> None:
    """A repo with no workflows passes."""
    assert run(repo, "run-zizmor.sh").returncode == 0


def test_zizmor_fails_an_unpinned_action(repo: Path, run: Run) -> None:
    """An action pinned to a tag, not a commit SHA, fails."""
    add(
        repo,
        {
            ".github/workflows/ci.yaml": ("---\nname: ci\non: push\npermissions: {}\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v5\n"),
        },
    )
    result: subprocess.CompletedProcess[str] = run(repo, "run-zizmor.sh")
    assert result.returncode != 0
    assert "unpinned" in result.stdout


def test_zizmor_rejects_an_unknown_persona(repo: Path, run: Run) -> None:
    """An argument zizmor rejects fails the script."""
    assert run(repo, "run-zizmor.sh", "--persona", "nope").returncode == 1


# --- gitleaks


def test_gitleaks_passes_a_clean_history(repo: Path, run: Run) -> None:
    """A history with no secrets passes."""
    add(repo, {"a.txt": "nothing secret\n"})
    git(repo, "commit", "--quiet", "-m", "clean")
    assert run(repo, "run-gitleaks.sh").returncode == 0


def test_gitleaks_finds_a_committed_secret(repo: Path, run: Run) -> None:
    """A GitHub token in a commit fails."""
    add(repo, {"config.txt": 'github_token = "ghp_' + "Z3x9Qm2LkP7vR4tY8wN1bC6dF0hJ5sA2eG7u" + '"\n'})
    git(repo, "commit", "--quiet", "-m", "oops")
    result: subprocess.CompletedProcess[str] = run(repo, "run-gitleaks.sh")
    assert result.returncode != 0
    assert "leaks found" in result.stdout + result.stderr


# --- trivy


@pytest.mark.integration  # downloads trivy's vulnerability database
def test_trivy_reads_jetstreams_and_the_repos_exceptions(repo: Path, run: Run) -> None:
    """A finding is ignored when either .jetstream/trivyignore or .trivyignore lists it, until the exception expires."""
    add(repo, {"requirements.txt": "requests==2.31.0\n"})  # has known MEDIUM advisories
    found: subprocess.CompletedProcess[str] = run(repo, "run-trivy.sh")
    assert found.returncode != 0
    ids: list[str] = sorted(set(re.findall(r"CVE-\d{4}-\d+", found.stdout)))
    assert ids, found.stdout
    exceptions: str = "".join(f"{vuln_id} exp:2099-01-01\n" for vuln_id in ids)

    (repo / ".jetstream").mkdir()
    (repo / ".jetstream" / "trivyignore").write_text(exceptions)
    assert run(repo, "run-trivy.sh").returncode == 0

    (repo / ".jetstream" / "trivyignore").unlink()
    (repo / ".trivyignore").write_text(exceptions)
    assert run(repo, "run-trivy.sh").returncode == 0

    (repo / ".trivyignore").write_text("".join(f"{vuln_id} exp:2000-01-01\n" for vuln_id in ids))  # expired
    assert run(repo, "run-trivy.sh").returncode != 0


# --- unit-tests


def test_unit_tests_pass_when_there_are_no_tests(repo: Path, run: Run) -> None:
    """A repo with no tests passes, though pytest exits 5 when it collects none."""
    assert run(repo, "run-unit-tests.sh").returncode == 0


def test_unit_tests_fail_a_failing_test_but_skip_integration_tests(repo: Path, run: Run) -> None:
    """A failing test fails the hook, and a test marked integration isn't run."""
    add(
        repo,
        {
            "pyproject.toml": '[tool.pytest.ini_options]\nmarkers = ["integration: slow"]\n',
            "tests/test_a.py": ("import pytest\n\n\ndef test_fails():\n    assert False\n\n\n@pytest.mark.integration\ndef test_integration():\n    assert False\n"),
        },
    )
    result: subprocess.CompletedProcess[str] = run(repo, "run-unit-tests.sh")
    assert result.returncode == 1
    assert "1 failed, 1 deselected" in result.stdout


# --- d2-compile and check-svg


def test_check_svg_passes_a_compiled_diagram_and_fails_a_stale_one(repo: Path, run: Run) -> None:
    """An SVG compiled from its D2 source passes, and fails once the source changes."""
    add(repo, {"docs/images/d2/flow.d2": "a -> b\n"})
    assert run(repo, "run-d2-compile.sh").returncode == 0
    git(repo, "add", ".")
    assert run(repo, "run-check-svg.sh").returncode == 0

    add(repo, {"docs/images/d2/flow.d2": "a -> c\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-check-svg.sh")
    assert result.returncode == 1
    assert "Stale SVG: docs/images/flow.svg" in result.stderr


def test_check_svg_fails_an_svg_without_a_source(repo: Path, run: Run) -> None:
    """An SVG in an images/ folder with no D2 source fails; one elsewhere isn't checked."""
    add(repo, {"docs/images/orphan.svg": '<svg xmlns="http://www.w3.org/2000/svg"/>\n', "logo.svg": "<svg/>\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-check-svg.sh")
    assert result.returncode == 1
    assert "Missing source: docs/images/orphan.svg" in result.stderr
    assert "logo.svg" not in result.stderr


def test_d2_compile_fails_a_source_outside_images_d2(repo: Path, run: Run) -> None:
    """A D2 source must be in an images/d2/ folder, so its SVG's place is known."""
    add(repo, {"docs/flow.d2": "a -> b\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-d2-compile.sh")
    assert result.returncode == 1
    assert "outside an images/d2 directory: docs/flow.d2" in result.stderr


# --- no-commit-to-branch


def test_no_commit_to_branch(repo: Path, run: Run) -> None:
    """Committing on main fails, but on any other branch, a branch named as an argument, or a detached HEAD, it passes."""
    git(repo, "commit", "--quiet", "-m", "first")
    assert run(repo, "run-no-commit-to-branch.sh").returncode == 0  # on work

    git(repo, "checkout", "--quiet", "-b", "main")
    result: subprocess.CompletedProcess[str] = run(repo, "run-no-commit-to-branch.sh")
    assert result.returncode == 1
    assert "Don't commit directly to main" in result.stderr
    assert run(repo, "run-no-commit-to-branch.sh", "release").returncode == 0

    git(repo, "checkout", "--quiet", "--detach")
    assert run(repo, "run-no-commit-to-branch.sh").returncode == 0
