"""``jetstream new-repo``: a new repo's first files, then ``jetstream sync`` (decision 19).

It writes the files a repo owns from then on: ``pyproject.toml``, with the jetstream
pin and ``[tool.jetstream] packs``; ``README.md``, ``CONTRIBUTING.md`` and
``CLAUDE.md``; the ``.trivyignore`` starter; and, with the python pack, the
``.pip-audit-ignore`` starter, a package to build, and ``pyproject.toml``'s
``[build-system]``, ``[project.urls]`` and hatch keys (decision 7). Then ``sync``
writes everything jetstream owns.

It runs no subprocess: the ``jetstream-new-repo`` skill creates the GitHub repo,
runs this in its clone (with ``uvx``, before there's a ``.venv``), and then
``cfg4dev.sh``, which runs ``uv sync``.
"""

from __future__ import annotations

import re
from importlib.metadata import version
from typing import TYPE_CHECKING, Final

import tomlkit

from jetstream import sync

if TYPE_CHECKING:
    from pathlib import Path

DISTRIBUTION: Final[str] = "cloudfeaster-jetstream"
JETSTREAM_GIT: Final[str] = "https://github.com/cloudfeaster/jetstream"
ORG_URL: Final[str] = "https://github.com/cloudfeaster"

# The python pack's starting build backend; the repo owns it from then on.
# Kept in step with jetstream's own [build-system] by a test.
HATCHLING: Final[str] = "hatchling==1.33.0"

# Packs new-repo can start a repo with. The website pack has no files yet.
READY_PACKS: Final[tuple[str, ...]] = ("core", "python")

# A project name (PEP 508).
NAME: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")

# Docs for setting an org or a repo up, not for working in one, so CLAUDE.md doesn't import them.
SETUP_DOCS: Final[frozenset[str]] = frozenset({"adopting.md", "dependabot-alerts.md", "jetstream-update.md", "new-repo.md", "org-setup.md"})
FIRST_DOC: Final[str] = "behavioral-guidelines.md"

EXCEPTION_EXAMPLE: Final[str] = "#   CVE-2026-12345 exp:2026-12-01  # fixed in foo 1.2.3 (2026-11-26), inside the 7-day cooldown\n"


class NewRepoError(Exception):
    """A reason new-repo can't start the repo, reported in one line."""


def pyproject(name: str, description: str, packs: tuple[str, ...]) -> str:
    """Return the repo's first pyproject.toml; ``sync`` then adds jetstream's keys."""
    python: bool = "python" in packs
    lines: list[str] = []
    if python:
        lines += ["[build-system]", f'requires = ["{HATCHLING}"]', 'build-backend = "hatchling.build"', ""]
    lines += [
        "[project]",
        f"name = {tomlkit.string(name).as_string()}",
        'version = "0.0.0"',
        f"description = {tomlkit.string(description).as_string()}",
        "dependencies = []",
        "",
    ]
    if python:
        lines += ["[project.urls]", f'Repository = "{ORG_URL}/{name}"', ""]
    lines += ["[dependency-groups]", "dev = [", f'    "{DISTRIBUTION}[{",".join(packs)}]",', "]", ""]
    if python:
        lines += ["[tool.hatch.build.targets.wheel]", f'packages = ["{package_name(name)}"]', ""]
    else:
        lines += ["[tool.uv]", "package = false  # not a Python package: uv only manages the dev environment", ""]
    lines += [
        "[tool.uv.sources]",
        "# Pinned to a release tag, which the jetstream-update workflow bumps.",
        f'{DISTRIBUTION} = {{ git = "{JETSTREAM_GIT}", tag = "v{version(DISTRIBUTION)}" }}',
        "",
        "[tool.jetstream]",
        f"packs = [{', '.join(f'"{pack}"' for pack in packs)}]",
    ]
    return "\n".join(lines) + "\n"


def package_name(name: str) -> str:
    """Return the import name of the project ``name``'s package."""
    return name.replace("-", "_").replace(".", "_").lower()


def claude_md(packs: tuple[str, ...]) -> str:
    """Return CLAUDE.md, importing each doc jetstream writes for ``packs`` that's about working in the repo."""
    docs: list[str] = sorted(path for path in sync.expected(packs).files if path.startswith(f"{sync.DOCS_DIR}/") and path.rsplit("/", 1)[-1] not in SETUP_DOCS)
    docs.sort(key=lambda path: (not path.endswith(f"/core/{FIRST_DOC}"), not path.startswith(f"{sync.DOCS_DIR}/core/")))
    imports: str = "".join(f"@{path}\n" for path in docs)
    return f"# CLAUDE.md\n\nGuidance for Claude Code in this repo. It follows the conventions jetstream ships, imported below from `.jetstream/docs/`, which `jetstream sync` writes.\n\n{imports}"


def contributing_md(packs: tuple[str, ...]) -> str:
    """Return CONTRIBUTING.md, pointing at jetstream's docs."""
    docs: list[str] = [
        "- [dev-workflow.md](.jetstream/docs/core/dev-workflow.md): how a change gets to `main`;",
        "- [dev-environment.md](.jetstream/docs/core/dev-environment.md): the tools and checks;",
    ]
    if "python" in packs:
        docs.append("- [python.md](.jetstream/docs/python/python.md): the Python conventions;")
    docs[-1] = docs[-1].removesuffix(";") + "."
    return (
        "# Contributing\n\n"
        f"This repo's development environment is set up by [jetstream]({JETSTREAM_GIT}). Install [uv](https://docs.astral.sh/uv/), then:\n\n"
        "```bash\nsource cfg4dev.sh\n```\n\n"
        "jetstream's docs, in `.jetstream/docs/`, say how to work here:\n\n" + "\n".join(docs) + "\n"
    )


def ignore_starter(scanner: str, tools_file: str) -> str:
    """Return the starter for the repo's own exceptions file for ``scanner``."""
    return (
        f"# Temporary exceptions for {scanner} findings in this repo's own dependencies.\n"
        f"# Findings in jetstream's tools are excepted in jetstream's {tools_file}, in a\n"
        "# jetstream release, never here (.jetstream/docs/core/dev-environment.md,\n"
        '# "Vulnerabilities").\n'
        "#\n"
        "# One line per vulnerability, expiring 7 days out, so it's reviewed again:\n"
        "#\n" + EXCEPTION_EXAMPLE
    )


def starter_files(name: str, description: str, packs: tuple[str, ...]) -> dict[str, str]:
    """Return the files new-repo writes, by path, before ``sync``."""
    found: dict[str, str] = {
        "pyproject.toml": pyproject(name, description, packs),
        "README.md": f"# {name}\n\n{description}\n\nTo work on it, see [CONTRIBUTING.md](CONTRIBUTING.md).\n",
        "CONTRIBUTING.md": contributing_md(packs),
        "CLAUDE.md": claude_md(packs),
        ".trivyignore": ignore_starter("trivy", ".jetstream/trivyignore"),
    }
    if "python" in packs:
        found[".pip-audit-ignore"] = ignore_starter("pip-audit", ".jetstream/pip-audit-ignore")
        found[f"{package_name(name)}/__init__.py"] = f'"""The {package_name(name)} package."""\n'
    return found


def new_repo(root: Path, description: str, packs: tuple[str, ...], name: str | None = None) -> list[str]:
    """Write a new repo's first files into ``root``, then ``sync``; return every file written."""
    name = name or root.name
    if not NAME.match(name):
        msg: str = f"{name!r} isn't a valid project name: use letters, digits, '-', '_' and '.'"
        raise NewRepoError(msg)
    unready: list[str] = [pack for pack in packs if pack not in READY_PACKS]
    if unready:
        msg: str = f"the {', '.join(unready)} pack isn't ready for new repos yet"
        raise NewRepoError(msg)
    packs = tuple(pack for pack in sync.PACKS if pack in {"core", *packs})
    if not description.strip():
        msg: str = "the description can't be empty"
        raise NewRepoError(msg)
    if "python" in packs and not package_name(name).isidentifier():
        msg: str = f"{name!r} can't be a Python package name: start it with a letter"
        raise NewRepoError(msg)

    files: dict[str, str] = starter_files(name, description, packs)
    existing: list[str] = sorted(path for path in files if (root / path).exists())
    if existing:
        msg: str = f"new-repo starts an empty repo, but it already has {', '.join(existing)}"
        raise NewRepoError(msg)
    for path, content in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(content)
    return [*files, *(path for path in sync.sync(root) if path not in files)]
