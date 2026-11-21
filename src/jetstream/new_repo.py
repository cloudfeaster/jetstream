"""``jetstream new-repo``: a new repo's first files, then ``jetstream sync`` (decision 19).

It writes the files a repo owns from then on, from each pack's ``starters/<pack>/``:

- each file there is a ``string.Template``, filled in with the repo's ``$name``,
  ``$description``, ``$package`` (its Python import name), ``$tag`` (the jetstream
  release that's running), ``$extras`` and ``$packs``; its path is a template
  too, and a ``.tmpl`` suffix is dropped (so jetstream's own linters skip it);
- each pack's ``pyproject.toml`` is added after the earlier packs' (a pack
  can't set a key an earlier one set), and a repo whose starters define no
  ``[build-system]`` isn't a Python package (``[tool.uv] package = false``);
- ``CLAUDE.md`` imports each doc the packs write for working in the repo, and
  ``CONTRIBUTING.md``'s ``$pack_docs`` lists the docs of each pack after core.

Then ``sync`` writes everything jetstream owns. A pack can start a repo once
it has a ``starters/<pack>/`` folder.

It runs no subprocess: the ``jetstream-new-repo`` skill creates the GitHub repo,
runs this in its clone (with ``uvx``, before there's a ``.venv``), and then
``cfg4dev.sh``, which runs ``uv sync``.
"""

from __future__ import annotations

import re
import string
from importlib.metadata import version
from typing import TYPE_CHECKING, Final

import tomlkit

from jetstream import sync

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable
    from pathlib import Path

DISTRIBUTION: Final[str] = "cloudfeaster-jetstream"
STARTERS: Final[Traversable] = sync.PACKAGE / "starters"
TEMPLATE_SUFFIX: Final[str] = ".tmpl"
PYPROJECT: Final[str] = "pyproject.toml"
NOT_A_PACKAGE: Final[str] = "not a Python package: uv only manages the dev environment"

# A project name (PEP 508).
NAME: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")

# Docs for setting an org or a repo up, not for working in one, so CLAUDE.md doesn't import them.
SETUP_DOCS: Final[frozenset[str]] = frozenset({"adopting.md", "dependabot-alerts.md", "jetstream-update.md", "new-repo.md", "org-setup.md"})
FIRST_DOC: Final[str] = "behavioral-guidelines.md"


class NewRepoError(Exception):
    """A reason new-repo can't start the repo, reported in one line."""


def package_name(name: str) -> str:
    """Return the import name of the project ``name``'s package."""
    return name.replace("-", "_").replace(".", "_").lower()


def doc_pack(path: str) -> str:
    """Return the pack of a doc at ``.jetstream/docs/<pack>/<doc>``."""
    return path.split("/")[2]


def working_docs(packs: tuple[str, ...]) -> list[str]:
    """Return the docs jetstream writes for ``packs`` that are about working in the repo: behavioral guidelines, then core's, then each pack's."""
    docs: list[str] = sorted(path for path in sync.expected(packs).files if path.startswith(f"{sync.DOCS_DIR}/") and path.rsplit("/", 1)[-1] not in SETUP_DOCS)
    docs.sort(key=lambda path: (not path.endswith(f"/core/{FIRST_DOC}"), sync.PACKS.index(doc_pack(path))))
    return docs


def claude_md(packs: tuple[str, ...]) -> str:
    """Return CLAUDE.md, importing each doc about working in the repo."""
    imports: str = "".join(f"@{path}\n" for path in working_docs(packs))
    return f"# CLAUDE.md\n\nGuidance for Claude Code in this repo. It follows the conventions jetstream ships, imported below from `.jetstream/docs/`, which `jetstream sync` writes.\n\n{imports}"


def pack_docs(packs: tuple[str, ...]) -> str:
    """Return the lines CONTRIBUTING.md's list of docs gets for each pack after core, each a doc and its heading, each starting with a newline."""
    lines: list[str] = []
    for path in working_docs(packs):
        if doc_pack(path) != "core":
            heading: str = (sync.PACKAGE / "docs" / path.split("/", 2)[2]).read_text().splitlines()[0].removeprefix("# ")
            lines.append(f"\n- [{path.rsplit('/', 1)[-1]}]({path}): {heading}")
    return "".join(lines)


def starters(packs: tuple[str, ...]) -> dict[str, list[str]]:
    """Return each starter's template path, with the texts the packs give it, in pack order."""
    found: dict[str, list[str]] = {}
    for pack in packs:
        for path, entry in sync.walk(STARTERS / pack).items():
            found.setdefault(path.removesuffix(TEMPLATE_SUFFIX), []).append(entry.read_text())
    return found


def render(template: str, values: dict[str, str]) -> str:
    """Return ``template`` filled in with ``values``, ending in exactly one newline."""
    return string.Template(template).substitute(values).rstrip("\n") + "\n"


def pyproject(texts: list[str], values: dict[str, str]) -> str:
    """Return pyproject.toml from each pack's starter, with ``[tool.uv] package = false`` unless one sets ``[build-system]``."""
    description: str = tomlkit.string(values["description"]).as_string()[1:-1]  # escaped for a TOML basic string
    document: tomlkit.TOMLDocument = tomlkit.parse("\n".join(render(text, {**values, "description": description}) for text in texts))
    if "build-system" not in document:
        sync.set_key(document, ("tool", "uv", "package"), tomlkit.item(value=False).comment(NOT_A_PACKAGE))
    return tomlkit.dumps(document)


def starter_files(name: str, description: str, packs: tuple[str, ...]) -> dict[str, str]:
    """Return the files new-repo writes, by path, before ``sync``."""
    values: dict[str, str] = {
        "name": name,
        "description": description,
        "package": package_name(name),
        "tag": f"v{version(DISTRIBUTION)}",
        "extras": ",".join(packs),
        "packs": ", ".join(f'"{pack}"' for pack in packs),
        "pack_docs": pack_docs(packs),
    }
    found: dict[str, str] = {"CLAUDE.md": claude_md(packs)}
    for path, texts in starters(packs).items():
        target: str = string.Template(path).substitute(values)
        if path == PYPROJECT:
            found[target] = pyproject(texts, values)
        elif len(texts) > 1:
            msg: str = f"packs both start {path}"
            raise NewRepoError(msg)  # a bug in jetstream, caught by its tests
        else:
            found[target] = render(texts[0], values)
    return found


def uses_package(packs: tuple[str, ...]) -> bool:
    """Return whether any of the packs' starters uses ``$package``, so the name must make a Python package name."""
    return any("$package" in path or any("$package" in text for text in texts) for path, texts in starters(packs).items())


def check_inputs(name: str, description: str, packs: tuple[str, ...]) -> None:
    """Raise NewRepoError, in one line, if new-repo can't start a repo from these inputs."""
    if not NAME.match(name):
        msg: str = f"{name!r} isn't a valid project name: use letters, digits, '-', '_' and '.'"
        raise NewRepoError(msg)
    unready: list[str] = [pack for pack in packs if not (STARTERS / pack).is_dir()]
    if unready:
        msg: str = f"the {', '.join(unready)} pack isn't ready for new repos yet"
        raise NewRepoError(msg)
    if not description.strip():
        msg: str = "the description can't be empty"
        raise NewRepoError(msg)
    if uses_package(packs) and not package_name(name).isidentifier():
        msg: str = f"{name!r} can't be a Python package name: start it with a letter"
        raise NewRepoError(msg)


def new_repo(root: Path, description: str, packs: tuple[str, ...], name: str | None = None) -> list[str]:
    """Write a new repo's first files into ``root``, then ``sync``; return every file written."""
    name = name or root.name
    packs = tuple(pack for pack in sync.PACKS if pack in {"core", *packs})
    check_inputs(name, description, packs)

    files: dict[str, str] = starter_files(name, description, packs)
    existing: list[str] = sorted(path for path in files if (root / path).exists())
    if existing:
        msg: str = f"new-repo starts an empty repo, but it already has {', '.join(existing)}"
        raise NewRepoError(msg)
    for path, content in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(content)
    return [*files, *(path for path in sync.sync(root) if path not in files)]
