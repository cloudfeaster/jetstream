"""Tests for the core pack's run-*.sh scripts, each run in a throwaway git repo.

The scripts are run from this .venv/bin, with a PATH that doesn't include it,
to check that each one finds the tools installed next to it.
"""

import functools
import json
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
    "bash",
    "basename",
    "cat",
    "cmp",
    "cp",
    "date",
    "dirname",
    "env",
    "git",
    "grep",
    "mkdir",
    "ln",
    "mktemp",
    "node",  # run-lychee.sh reads the site's Astro config
    "rm",
    "rmdir",
    "sed",
    "uv",
)


def test_installed_scripts_match_their_source() -> None:
    """The scripts these tests run, in .venv/bin, are the ones in src/jetstream/bin: after editing one, `uv sync` installs it."""
    stale: list[str] = []
    for script in sorted((ROOT / "src" / "jetstream" / "bin").glob("*/*.sh")):
        installed: Path = VENV_BIN / script.name
        if not installed.is_file() or installed.read_bytes() != script.read_bytes():
            stale.append(script.name)
    assert not stale, f"run `uv sync`: .venv/bin has no copy, or an older copy, of {', '.join(stale)}, so the tests would check that, not your change"


def git(repo: Path, *args: str) -> str:
    """Run git in ``repo`` and return its output."""
    result: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603 (only the tests' own arguments)
        ["git", *args],  # noqa: S607 (git from PATH, as people run it)
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
    return subprocess.run(  # noqa: S603 (only the tests' own arguments)
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


# --- bandit, deptry and pyscn


# A call bandit flags (B310), and ruff doesn't: the URL is https.
URLOPEN_PYTHON: Final[str] = '"""A module."""\n\nimport urllib.request\n\nurllib.request.urlopen("https://example.com")\n'


def test_bandit_passes_good_python(repo: Path, run: Run) -> None:
    """A module with no security findings passes, and an assert is allowed."""
    add(repo, {"pyproject.toml": PYTHON_PYPROJECT, "a.py": GOOD_PYTHON + "\nassert ANSWER\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-bandit.sh")
    assert result.returncode == 0, result.stdout + result.stderr


def test_bandit_fails_a_finding(repo: Path, run: Run) -> None:
    """A call to urlopen fails bandit's B310."""
    add(repo, {"pyproject.toml": PYTHON_PYPROJECT, "a.py": URLOPEN_PYTHON})
    result: subprocess.CompletedProcess[str] = run(repo, "run-bandit.sh")
    assert result.returncode != 0
    assert "B310" in result.stdout


def test_bandit_skips_tests(repo: Path, run: Run) -> None:
    """A finding under tests/ isn't reported: ruff's S rules check the tests."""
    add(repo, {"pyproject.toml": PYTHON_PYPROJECT, "tests/test_a.py": URLOPEN_PYTHON})
    result: subprocess.CompletedProcess[str] = run(repo, "run-bandit.sh")
    assert result.returncode == 0, result.stdout + result.stderr


def test_bandit_passes_with_no_python(repo: Path, run: Run) -> None:
    """A repo with no *.py files passes."""
    assert run(repo, "run-bandit.sh").returncode == 0


# A project with no dependencies, as deptry reads it.
DEPTRY_PYPROJECT: Final[str] = '[project]\nname = "a"\nversion = "0"\ndependencies = []\n'


def test_deptry_passes_declared_imports(repo: Path, run: Run) -> None:
    """A module importing only the standard library passes."""
    add(repo, {"pyproject.toml": DEPTRY_PYPROJECT, "a.py": '"""A module."""\n\nimport os\n'})
    result: subprocess.CompletedProcess[str] = run(repo, "run-deptry.sh")
    assert result.returncode == 0, result.stdout + result.stderr


def test_deptry_fails_an_undeclared_import(repo: Path, run: Run) -> None:
    """Importing a package the project doesn't declare fails DEP001."""
    add(repo, {"pyproject.toml": DEPTRY_PYPROJECT, "a.py": '"""A module."""\n\nimport not_a_dependency\n'})
    result: subprocess.CompletedProcess[str] = run(repo, "run-deptry.sh")
    assert result.returncode != 0
    assert "DEP001" in result.stderr


def test_pyscn_passes_good_python(repo: Path, run: Run) -> None:
    """Simple code scores above the floor, and only the score is printed."""
    add(repo, {"a.py": GOOD_PYTHON})
    result: subprocess.CompletedProcess[str] = run(repo, "run-pyscn.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert re.fullmatch(r"pyscn: health score \d+ \(A\)\n", result.stdout)
    assert result.stderr == ""


def test_pyscn_fails_below_the_floor(repo: Path, run: Run) -> None:
    """Four copies of a 30-branch function score below 90."""
    body: str = "".join(f"    if x == {i}:\n        y = x + {i}\n        return y * 2\n" for i in range(30))
    functions: str = "".join(f'\n\ndef f{n}(x: int) -> int:\n    """Return something."""\n{body}    return 0\n' for n in range(4))
    add(repo, {"a.py": '"""A module."""\n' + functions})
    result: subprocess.CompletedProcess[str] = run(repo, "run-pyscn.sh")
    assert result.returncode != 0
    assert "is below 90" in result.stderr


def test_pyscn_passes_with_no_python(repo: Path, run: Run) -> None:
    """A repo with no *.py files passes."""
    assert run(repo, "run-pyscn.sh").returncode == 0


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


# --- pip-audit and licensecheck


def lock(repo: Path, *dependencies: str) -> None:
    """Give ``repo`` a project depending on ``dependencies``, with its uv.lock, and stage them."""
    listed: str = ", ".join(f'"{dependency}"' for dependency in dependencies)
    add(repo, {"pyproject.toml": PYTHON_PYPROJECT + f'\n[project]\nname = "a"\nversion = "0"\nrequires-python = "==3.13.*"\ndependencies = [{listed}]\n'})
    uv: str | None = shutil.which("uv")
    assert uv is not None
    subprocess.run([uv, "lock", "--quiet"], cwd=repo, check=True)  # noqa: S603 (only the tests' own arguments)
    git(repo, "add", "uv.lock")


@pytest.mark.integration  # locks from PyPI, and looks up advisories
def test_pip_audit_reads_jetstreams_and_the_repos_exceptions(repo: Path, run: Run) -> None:
    """A finding is ignored when either .jetstream/pip-audit-ignore or .pip-audit-ignore lists it, until the exception expires."""
    lock(repo, "jinja2==3.1.4")  # has known advisories
    found: subprocess.CompletedProcess[str] = run(repo, "run-pip-audit.sh")
    assert found.returncode != 0
    ids: list[str] = sorted(set(re.findall(r"\b(?:PYSEC|GHSA)-[\w-]+", found.stdout)))
    assert ids, found.stdout + found.stderr
    exceptions: str = "".join(f"{vuln_id} exp:2099-01-01  # why\n" for vuln_id in ids)

    (repo / ".jetstream").mkdir()
    (repo / ".jetstream" / "pip-audit-ignore").write_text(exceptions)
    result: subprocess.CompletedProcess[str] = run(repo, "run-pip-audit.sh")
    assert result.returncode == 0, result.stdout + result.stderr

    (repo / ".jetstream" / "pip-audit-ignore").unlink()
    (repo / ".pip-audit-ignore").write_text(exceptions)
    assert run(repo, "run-pip-audit.sh").returncode == 0

    (repo / ".pip-audit-ignore").write_text("".join(f"{vuln_id} exp:2000-01-01\n" for vuln_id in ids))  # expired
    assert run(repo, "run-pip-audit.sh").returncode != 0


def test_pip_audit_fails_a_malformed_exception(repo: Path, run: Run) -> None:
    """An exception with something other than exp:YYYY-MM-DD after its ID fails, naming the file."""
    add(repo, {".pip-audit-ignore": "PYSEC-2026-1 2026-12-01\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-pip-audit.sh")
    assert result.returncode != 0
    assert ".pip-audit-ignore: 'PYSEC-2026-1 2026-12-01': expected exp:YYYY-MM-DD" in result.stderr


def test_licensecheck_passes_a_project_with_no_dependencies(repo: Path, run: Run) -> None:
    """A project with no product dependencies yet, such as a new repo, has no licenses to check, so it passes."""
    lock(repo)
    result: subprocess.CompletedProcess[str] = run(repo, "run-licensecheck.sh")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.integration  # locks from PyPI, and looks up licenses
def test_licensecheck_passes_an_allowed_license(repo: Path, run: Run) -> None:
    """An MIT-licensed dependency passes."""
    lock(repo, "tomlkit==0.15.2")
    result: subprocess.CompletedProcess[str] = run(repo, "run-licensecheck.sh")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.integration  # locks from PyPI, and looks up licenses
def test_licensecheck_fails_a_license_jetstream_doesnt_allow(repo: Path, run: Run) -> None:
    """An LGPL-licensed dependency fails, unless it's one of jetstream's ignore_packages."""
    lock(repo, "paramiko==4.0.0")
    result: subprocess.CompletedProcess[str] = run(repo, "run-licensecheck.sh")
    assert result.returncode != 0
    assert "paramiko" in result.stdout

    pyproject: str = (repo / "pyproject.toml").read_text().replace("ignore_packages = []", 'ignore_packages = ["paramiko"]')
    (repo / "pyproject.toml").write_text(pyproject)
    result = run(repo, "run-licensecheck.sh")
    assert result.returncode == 0, result.stdout + result.stderr


# --- prune constraints and exclude-newer-package

# The prune scripts' exit status when they couldn't check the entries.
PRUNE_ERROR: Final[int] = 2


def lock_project(repo: Path, uv_table: str) -> None:
    """Give ``repo`` a project depending on flask 3.0.0 (which needs Jinja2>=3.1.2), with ``uv_table`` and its uv.lock."""
    add(repo, {"pyproject.toml": f'[project]\nname = "a"\nversion = "0"\nrequires-python = "==3.13.*"\ndependencies = ["flask==3.0.0"]\n\n[tool.uv]\n{uv_table}'})
    uv: str | None = shutil.which("uv")
    assert uv is not None
    subprocess.run([uv, "lock", "--quiet"], cwd=repo, check=True)  # noqa: S603 (only the tests' own arguments)
    git(repo, "add", "uv.lock")


@pytest.mark.parametrize("script", ["run-prune-constraints.sh", "run-prune-exclude-newer-package.sh"])
def test_prune_passes_with_nothing_to_check(repo: Path, run: Run, script: str) -> None:
    """A repo with no entries passes without locking anything."""
    add(repo, {"pyproject.toml": '[project]\nname = "a"\n'})
    result: subprocess.CompletedProcess[str] = run(repo, script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "prune: no [tool.uv]" in result.stdout


@pytest.mark.integration  # locks from PyPI
def test_prune_constraints_names_only_the_redundant_one(repo: Path, run: Run) -> None:
    """A floor flask already requires is redundant; a higher one is still needed; the repo's files don't change."""
    lock_project(repo, 'constraint-dependencies = [\n    "jinja2>=3.1.6",  # CVE-2025-27516\n    "Jinja2>=3.1.2",\n]\n')
    before: str = (repo / "pyproject.toml").read_text() + (repo / "uv.lock").read_text()
    result: subprocess.CompletedProcess[str] = run(repo, "run-prune-constraints.sh")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "prune: jinja2>=3.1.6: still needed" in result.stdout
    assert "prune: Jinja2>=3.1.2: redundant" in result.stdout
    assert (repo / "pyproject.toml").read_text() + (repo / "uv.lock").read_text() == before


@pytest.mark.integration  # locks from PyPI
def test_prune_exclude_newer_package_names_an_override_that_changes_nothing(repo: Path, run: Run) -> None:
    """An override for a package locked at an old release is redundant."""
    lock_project(repo, 'exclude-newer = "7 days"\nexclude-newer-package = { flask = "2026-11-19T00:00:00Z" }\n')
    result: subprocess.CompletedProcess[str] = run(repo, "run-prune-exclude-newer-package.sh")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "prune: flask: redundant, so remove it (3.0.0 locks without it)" in result.stdout


@pytest.mark.integration  # locks from PyPI
def test_prune_stops_when_the_lock_is_out_of_date(repo: Path, run: Run) -> None:
    """A uv.lock that doesn't match pyproject.toml is an error, not a list of redundant entries."""
    lock_project(repo, 'constraint-dependencies = ["jinja2>=3.1.6"]\n')
    (repo / "pyproject.toml").write_text((repo / "pyproject.toml").read_text().replace("flask==3.0.0", "flask==3.0.1"))
    result: subprocess.CompletedProcess[str] = run(repo, "run-prune-constraints.sh")
    assert result.returncode == PRUNE_ERROR, result.stdout + result.stderr
    assert "doesn't lock as it is, so nothing was checked" in result.stderr


# --- prune trivyignore and pip-audit-ignore


@pytest.mark.parametrize(("script", "exceptions"), [("run-prune-trivyignore.sh", ".trivyignore"), ("run-prune-pip-audit-ignore.sh", ".pip-audit-ignore")])
def test_prune_exceptions_passes_with_nothing_to_check(repo: Path, run: Run, script: str, exceptions: str) -> None:
    """Without an unexpired exception there's nothing to scan for, so the script passes without scanning."""
    add(repo, {"pyproject.toml": '[project]\nname = "a"\n', exceptions: "# a comment\nCVE-2000-0001 exp:2000-01-01  # expired\n"})
    result: subprocess.CompletedProcess[str] = run(repo, script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "exceptions to check" in result.stdout


@pytest.mark.integration  # downloads trivy's vulnerability database
def test_prune_trivyignore_names_only_the_redundant_exceptions(repo: Path, run: Run) -> None:
    """An exception matching a finding's CVE or GHSA ID is still needed; one matching nothing is redundant; an expired one isn't checked."""
    add(repo, {"requirements.txt": "requests==2.31.0\n"})  # has known MEDIUM advisories, among them CVE-2024-35195 (GHSA-9wx4-h78v-vm56)
    add(repo, {".trivyignore": "CVE-2024-35195 exp:2099-01-01  # why\nGHSA-9wx4-h78v-vm56 exp:2099-01-01\nCVE-2000-0001 exp:2099-01-01\nCVE-2000-0002 exp:2000-01-01\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-prune-trivyignore.sh")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "prune: .trivyignore: CVE-2024-35195: still needed" in result.stdout
    assert "prune: .trivyignore: GHSA-9wx4-h78v-vm56: still needed" in result.stdout
    assert "prune: .trivyignore: CVE-2000-0001: redundant" in result.stdout
    assert "CVE-2000-0002" not in result.stdout


@pytest.mark.integration  # locks from PyPI, and looks up advisories
def test_prune_pip_audit_ignore_names_only_the_redundant_exceptions(repo: Path, run: Run) -> None:
    """An exception matching a finding's ID or alias is still needed; one matching nothing is redundant."""
    lock(repo, "jinja2==3.1.4")  # has known advisories, among them PYSEC-2026-1475 (CVE-2024-56326)
    add(repo, {".pip-audit-ignore": "CVE-2024-56326 exp:2099-01-01  # why\nPYSEC-2000-1 exp:2099-01-01\n"})
    result: subprocess.CompletedProcess[str] = run(repo, "run-prune-pip-audit-ignore.sh")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "prune: .pip-audit-ignore: CVE-2024-56326: still needed" in result.stdout
    assert "prune: .pip-audit-ignore: PYSEC-2000-1: redundant" in result.stdout


# --- sync-dependabot-alerts


def fake_gh(tmp_path: Path, alerts: list[dict[str, object]]) -> tuple[Path, Path]:
    """Return a folder holding a fake gh, which lists ``alerts`` and logs every call, and its log."""
    folder: Path = tmp_path / "fake-gh"
    folder.mkdir()
    log: Path = tmp_path / "gh.log"
    log.touch()
    (tmp_path / "alerts.json").write_text(json.dumps(alerts))
    gh: Path = folder / "gh"
    gh.write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\nif [[ "$2" == --paginate ]]; then cat "{tmp_path / "alerts.json"}"; fi\n')
    gh.chmod(0o755)
    return folder, log


def dependabot_alert(number: int, cve: str, dismissed_comment: str | None = None) -> dict[str, object]:
    """Return a Dependabot alert for ``cve``, dismissed with ``dismissed_comment`` if it's given."""
    return {
        "number": number,
        "state": "open" if dismissed_comment is None else "dismissed",
        "dismissed_comment": dismissed_comment,
        "dismissed_reason": None if dismissed_comment is None else "tolerable_risk",
        "security_advisory": {"ghsa_id": f"GHSA-{number}", "identifiers": [{"type": "CVE", "value": cve}]},
    }


def test_sync_dependabot_alerts_applies_each_change(repo: Path, system_path: str, tmp_path: Path) -> None:
    """An accepted alert is dismissed, the sync's own dismissal with no exception is reopened, and anyone else's is left alone."""
    gh_folder: Path
    log: Path
    gh_folder, log = fake_gh(
        tmp_path,
        [
            dependabot_alert(1, "CVE-2099-1"),
            dependabot_alert(2, "CVE-2099-2", dismissed_comment="[jetstream exceptions] gone"),
            dependabot_alert(3, "CVE-2099-3", dismissed_comment="by hand"),
        ],
    )
    add(repo, {".trivyignore": "CVE-2099-1  # why\nCVE-2099-3\n"})
    result: subprocess.CompletedProcess[str] = run_script(f"{gh_folder}:{system_path}", repo, "run-sync-dependabot-alerts.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert log.read_text().splitlines() == [
        "api --paginate repos/{owner}/{repo}/dependabot/alerts?state=open,dismissed&per_page=100",
        "api --silent -X PATCH repos/{owner}/{repo}/dependabot/alerts/1 -f state=dismissed -f dismissed_reason=tolerable_risk -f dismissed_comment=[jetstream exceptions] .trivyignore (exp none): why",
        "api --silent -X PATCH repos/{owner}/{repo}/dependabot/alerts/2 -f state=open",
    ]
    assert "sync: #3 GHSA-3: dismissed (tolerable_risk) by someone other than the sync, so left alone" in result.stderr


def test_sync_dependabot_alerts_changes_nothing_when_they_match(repo: Path, system_path: str, tmp_path: Path) -> None:
    """With nothing to change, only the alerts are fetched."""
    gh_folder: Path
    log: Path
    gh_folder, log = fake_gh(tmp_path, [dependabot_alert(1, "CVE-2099-1")])
    result: subprocess.CompletedProcess[str] = run_script(f"{gh_folder}:{system_path}", repo, "run-sync-dependabot-alerts.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "sync: the Dependabot alerts already match the exceptions" in result.stdout
    assert len(log.read_text().splitlines()) == 1


# --- update-jetstream


def fake_gh_answering(tmp_path: Path, answers: dict[str, str]) -> tuple[Path, Path]:
    """Return a folder holding a fake gh, which logs every call and prints the answer for the first part of ``answers`` its arguments contain, and its log."""
    folder: Path = tmp_path / "fake-gh"
    folder.mkdir()
    log: Path = tmp_path / "gh.log"
    log.touch()
    cases: str = "".join(f'    *"{part}"*) printf "%s\\n" "{answer}" ;;\n' for part, answer in answers.items())
    gh: Path = folder / "gh"
    gh.write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\ncase "$*" in\n{cases}esac\n')
    gh.chmod(0o755)
    return folder, log


def jetstream_releases(tmp_path: Path, *tags: str) -> Path:
    """Return a git repo standing in for jetstream's, with ``tags``."""
    releases: Path = tmp_path / "jetstream"
    releases.mkdir()
    git(releases, "init", "--quiet")
    git(releases, "-c", "user.name=R", "-c", "user.email=r@example.com", "-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", "release")
    for tag in tags:
        git(releases, "tag", tag)
    return releases


def pin_jetstream(repo: Path, releases: Path, tag: str) -> None:
    """Pin ``repo``'s jetstream to ``tag`` of ``releases``, and commit it."""
    add(repo, {"pyproject.toml": f'[tool.uv.sources]\ncloudfeaster-jetstream = {{ git = "{releases}", tag = "{tag}" }}\n'})
    git(repo, "commit", "--quiet", "-m", "pin")


def test_update_jetstream_does_nothing_without_a_release_pin(repo: Path, system_path: str, tmp_path: Path) -> None:
    """A repo with no tag pin, such as jetstream itself, has nothing to update, and gh isn't called."""
    gh_folder: Path
    log: Path
    gh_folder, log = fake_gh_answering(tmp_path, {})
    add(repo, {"pyproject.toml": "[project]\nname = 'x'\n"})
    result: subprocess.CompletedProcess[str] = run_script(f"{gh_folder}:{system_path}", repo, "run-update-jetstream.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "nothing to update" in result.stdout
    assert not log.read_text()


def test_update_jetstream_closes_its_pull_request_once_the_pin_is_up_to_date(repo: Path, system_path: str, tmp_path: Path) -> None:
    """With the latest release pinned, an open update pull request is closed, with a comment."""
    pin_jetstream(repo, jetstream_releases(tmp_path, "v0.1.0", "v0.2.0"), "v0.2.0")
    gh_folder: Path
    log: Path
    gh_folder, log = fake_gh_answering(tmp_path, {"pulls?state=open": "7\tbuild(deps): update jetstream from v0.1.0 to v0.2.0"})
    result: subprocess.CompletedProcess[str] = run_script(f"{gh_folder}:{system_path}", repo, "run-update-jetstream.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "update: closing #7" in result.stdout
    calls: list[str] = log.read_text().splitlines()
    assert calls[1].startswith("api --silent -X POST repos/{owner}/{repo}/issues/7/comments")
    assert calls[2] == "api --silent -X PATCH repos/{owner}/{repo}/pulls/7 -f state=closed"


def test_update_jetstream_leaves_a_pull_request_that_is_already_up_to_date(repo: Path, system_path: str, tmp_path: Path) -> None:
    """An open pull request for the latest release, on the commit checked out, is left as it is."""
    pin_jetstream(repo, jetstream_releases(tmp_path, "v0.1.0", "v0.10.0", "v0.9.0"), "v0.1.0")
    head: str = git(repo, "rev-parse", "HEAD").strip()
    gh_folder: Path
    log: Path
    gh_folder, log = fake_gh_answering(
        tmp_path,
        {"pulls?state=open": "7\tbuild(deps): update jetstream from v0.1.0 to v0.10.0", "commits/jetstream/update": head},
    )
    result: subprocess.CompletedProcess[str] = run_script(f"{gh_folder}:{system_path}", repo, "run-update-jetstream.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "update: #7 already updates jetstream to v0.10.0" in result.stdout
    assert log.read_text().splitlines() == [
        'api repos/{owner}/{repo}/pulls?state=open&head={owner}:jetstream/update --jq .[] | "\\(.number)\\t\\(.title)"',
        "api repos/{owner}/{repo}/commits/jetstream/update --jq .parents[0].sha",
    ]
    assert not git(repo, "status", "--porcelain")


# --- astro check (website pack)

ASTRO_PACKAGES: Final[tuple[str, ...]] = ("astro", "@astrojs/check", "typescript")


def install_fake_astro(repo: Path) -> None:
    """Put the packages run-astro-check.sh needs in ``repo``'s node_modules, with an astro that only says it ran."""
    for package in ASTRO_PACKAGES:
        manifest: Path = repo / "node_modules" / package / "package.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": package}))
    astro: Path = repo / "node_modules" / ".bin" / "astro"
    astro.parent.mkdir()
    astro.write_text('#!/bin/bash\necho "fake astro $*"\n')
    astro.chmod(0o755)


def test_astro_check_runs_the_sites_astro(repo: Path, run: Run) -> None:
    """The hook runs `astro check` from the site's own node_modules."""
    install_fake_astro(repo)
    result: subprocess.CompletedProcess[str] = run(repo, "run-astro-check.sh")
    assert result.returncode == 0
    assert result.stdout == "fake astro check\n"


@pytest.mark.parametrize("missing", ASTRO_PACKAGES)
def test_astro_check_names_a_missing_package(repo: Path, run: Run, missing: str) -> None:
    """Without one of the packages astro check needs, the hook fails, naming it."""
    install_fake_astro(repo)
    shutil.rmtree(repo / "node_modules" / missing)
    result: subprocess.CompletedProcess[str] = run(repo, "run-astro-check.sh")
    assert result.returncode == 1
    assert f"{missing} isn't in node_modules" in result.stderr


# --- lychee (website pack)

BASE_PAGE: Final[str] = '<html lang="en"><head><title>Home</title></head><body><h1 id="top">Home</h1>{links}</body></html>'


def build_site(repo: Path, config: dict[str, str], links: list[str]) -> None:
    """Write an Astro config with ``config``'s keys, and a dist/ as astro build would, with ``links`` on its home page and an about page."""
    (repo / "astro.config.mjs").write_text(f"export default {json.dumps(config)};\n")
    page: str = BASE_PAGE.format(links="".join(f'<a href="{link}">link</a>' for link in links))
    (repo / "dist" / "about").mkdir(parents=True)
    (repo / "dist" / "index.html").write_text(page)
    (repo / "dist" / "about" / "index.html").write_text('<html lang="en"><head><title>About</title></head><body><h1 id="team">About</h1></body></html>')


SITE: Final[str] = "https://example.org"
LYCHEE_BROKEN_LINKS: Final[int] = 2  # lychee's exit code when a link is broken


@pytest.mark.parametrize(
    ("config", "links"),
    [
        ({}, ["/about/", "/about/#team", "#top", "about/"]),
        ({"site": SITE, "base": "/docs"}, ["/docs/about/", "/docs/about/#team", "#top", f"{SITE}/docs/about/"]),
        ({"site": f"{SITE}/", "base": "/a/b/"}, ["/a/b/about/", f"{SITE}/a/b/about/#team"]),
    ],
    ids=["no-base", "base", "nested-base-with-slashes"],
)
def test_lychee_passes_the_sites_own_links(repo: Path, run: Run, config: dict[str, str], links: list[str]) -> None:
    """Root-relative links under the site's base, and absolute links to the site itself, are checked against dist/."""
    build_site(repo, config, links)
    result: subprocess.CompletedProcess[str] = run(repo, "run-lychee.sh")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "link",
    ["/docs/missing/", "/docs/about/#nowhere", "#nowhere", "/about/", f"{SITE}/docs/missing/"],
    ids=["missing-page", "missing-fragment", "missing-local-fragment", "outside-the-base", "missing-absolute"],
)
def test_lychee_fails_a_broken_link(repo: Path, run: Run, link: str) -> None:
    """A link to a page or #fragment that isn't in dist/ fails, offline."""
    build_site(repo, {"site": SITE, "base": "/docs"}, [link])
    result: subprocess.CompletedProcess[str] = run(repo, "run-lychee.sh")
    assert result.returncode == LYCHEE_BROKEN_LINKS
    assert "1 Error" in result.stdout


@pytest.mark.parametrize("site", [f"{SITE}:443", "https://EXAMPLE.org/"], ids=["default-port", "upper-case-host"])
def test_lychee_checks_the_sites_own_links_however_site_is_written(repo: Path, run: Run, site: str) -> None:
    """The Astro config's site is compared as lychee writes URLs, so a broken absolute link to the site itself still fails offline rather than being skipped."""
    build_site(repo, {"site": site, "base": "/docs"}, [f"{SITE}/docs/missing/"])
    result: subprocess.CompletedProcess[str] = run(repo, "run-lychee.sh")
    assert result.returncode == LYCHEE_BROKEN_LINKS
    assert "1 Error" in result.stdout


def test_lychee_reads_a_typescript_config_with_an_enum(repo: Path, run: Run) -> None:
    """An astro.config.ts with TypeScript that type stripping can't handle, such as an enum, is still read."""
    build_site(repo, {}, ["/docs/about/"])
    (repo / "astro.config.mjs").unlink()
    (repo / "astro.config.ts").write_text('enum Paths {\n    Docs = "/docs",\n}\n\nexport default { site: "https://example.org", base: Paths.Docs };\n')
    result: subprocess.CompletedProcess[str] = run(repo, "run-lychee.sh")
    assert result.returncode == 0, result.stdout + result.stderr


def test_lychee_offline_skips_a_scheme_relative_link_to_another_site(repo: Path, run: Run) -> None:
    """A scheme-relative link (//host/path) is another site's, not a missing local file, so offline it's skipped."""
    build_site(repo, {"site": SITE}, ["//www.iana.org/"])
    result: subprocess.CompletedProcess[str] = run(repo, "run-lychee.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 Excluded" in result.stdout


def test_lychee_offline_skips_other_sites(repo: Path, run: Run) -> None:
    """Without --external, a link to another site isn't checked (and the test makes no network request)."""
    build_site(repo, {}, ["https://www.iana.org/"])
    result: subprocess.CompletedProcess[str] = run(repo, "run-lychee.sh")
    assert result.returncode == 0
    assert "1 Excluded" in result.stdout


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("no-dist", "no dist/: build the site first"),
        ("no-config", "no astro.config.mjs"),
    ],
)
def test_lychee_needs_a_built_site_and_its_config(repo: Path, run: Run, setup: str, message: str) -> None:
    """Without dist/ or an Astro config, the script says what's missing."""
    build_site(repo, {}, [])
    if setup == "no-dist":
        shutil.rmtree(repo / "dist")
    else:
        (repo / "astro.config.mjs").unlink()
    result: subprocess.CompletedProcess[str] = run(repo, "run-lychee.sh")
    assert result.returncode == 1
    assert message in result.stderr


def test_lychee_rejects_unknown_arguments(repo: Path, run: Run) -> None:
    """Only --external is accepted."""
    result: subprocess.CompletedProcess[str] = run(repo, "run-lychee.sh", "--offline")
    assert result.returncode == 1
    assert "usage: run-lychee.sh [--external]" in result.stderr


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


def test_integration_tests_run_only_the_integration_tests(repo: Path, run: Run) -> None:
    """run-integration-tests.sh runs the tests marked integration, and only those."""
    add(
        repo,
        {
            "pyproject.toml": '[tool.pytest.ini_options]\nmarkers = ["integration: slow"]\n',
            "tests/test_a.py": ("import pytest\n\n\ndef test_unit():\n    assert False\n\n\n@pytest.mark.integration\ndef test_integration():\n    assert False\n"),
        },
    )
    result: subprocess.CompletedProcess[str] = run(repo, "run-integration-tests.sh")
    assert result.returncode == 1
    assert "1 failed, 1 deselected" in result.stdout


def test_integration_tests_pass_when_there_are_none(repo: Path, run: Run) -> None:
    """A repo with no integration tests passes, though pytest exits 5 when it collects none."""
    add(repo, {"tests/test_a.py": "def test_unit():\n    pass\n"})
    assert run(repo, "run-integration-tests.sh").returncode == 0


# The python pack's keys, with pytest importing a.py from the repo's root.
COVERAGE_PYPROJECT: Final[str] = PYTHON_PYPROJECT + '\n[tool.pytest.ini_options]\npythonpath = ["."]\n'
COVERED_MODULE: Final[str] = "def double(x):\n    return 2 * x\n"
COVERED_MODULE_TEST: Final[str] = "from a import double\n\n\ndef test_double():\n    assert double(2) == 4\n"


def test_unit_tests_pass_above_the_coverage_floor(repo: Path, run: Run) -> None:
    """With coverage installed, as the python pack does, the tests run under it and it reports."""
    add(repo, {"pyproject.toml": COVERAGE_PYPROJECT, "a.py": COVERED_MODULE, "tests/test_a.py": COVERED_MODULE_TEST})
    result: subprocess.CompletedProcess[str] = run(repo, "run-unit-tests.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout
    assert re.search(r"^TOTAL .* 100%$", result.stdout, re.MULTILINE)


def test_unit_tests_fail_below_the_coverage_floor(repo: Path, run: Run) -> None:
    """Passing tests fail the hook when coverage is below fail_under; a file no test imports counts."""
    add(
        repo,
        {
            "pyproject.toml": COVERAGE_PYPROJECT,
            "a.py": COVERED_MODULE,
            "b.py": "def untested(x):\n" + "".join(f"    x = x + {i}\n" for i in range(10)) + "    return x\n",
            "tests/test_a.py": COVERED_MODULE_TEST,
        },
    )
    result: subprocess.CompletedProcess[str] = run(repo, "run-unit-tests.sh")
    assert result.returncode != 0
    assert "1 passed" in result.stdout
    assert "b.py" in result.stdout
    assert "fail-under=80" in result.stdout


def test_unit_tests_run_plain_pytest_without_coverage(repo: Path, run: Run, tmp_path: Path) -> None:
    """Without coverage installed next to it (core alone), the script runs pytest by itself."""
    bin_dir: Path = tmp_path / "core-bin"
    bin_dir.mkdir()
    shutil.copy(VENV_BIN / "run-unit-tests.sh", bin_dir)
    (bin_dir / "pytest").symlink_to(VENV_BIN / "pytest")
    add(repo, {"pyproject.toml": COVERAGE_PYPROJECT, "a.py": COVERED_MODULE, "tests/test_a.py": COVERED_MODULE_TEST})
    result: subprocess.CompletedProcess[str] = run(repo, str(bin_dir / "run-unit-tests.sh"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout
    assert "TOTAL" not in result.stdout
    assert not (repo / ".coverage").exists()


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
