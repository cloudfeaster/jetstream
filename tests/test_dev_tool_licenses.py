"""Every tool jetstream installs has a license licensing.md allows for a development tool.

That's any open-source license, GPL, LGPL and AGPL included, except that an
AGPL tool needs a review first. Licenses are compared by SPDX ID with the list
below, so one that isn't on it, or a missing one, fails until it's reviewed,
and a source-available license such as FSL-1.1-Apache-2.0 doesn't pass for
Apache. The product rule, which the python pack's python-licenses hook applies
to a repo's own dependencies, is a different one.
"""

import importlib.metadata
import json
import tomllib
from email.message import Message
from importlib.metadata import PackageMetadata
from pathlib import Path
from typing import Any, Final

import pytest
from packaging.requirements import Requirement
from packaging.utils import NormalizedName, canonicalize_name

from jetstream import npm_licenses

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DISTRIBUTION: Final[str] = "cloudfeaster-jetstream"
RECORDS: Final[dict[str, Any]] = tomllib.loads((ROOT / "dev-tool-licenses.toml").read_text())
BINARIES: Final[dict[str, Any]] = tomllib.loads((ROOT / "binaries.toml").read_text())

# The SPDX IDs that are open-source licenses, among those the tools jetstream
# installs have. A new ID fails until it's reviewed and added here, or, if it
# isn't open source and is a Node package's, the package is stubbed out
# (src/jetstream/node/lighthouse/stubs/). AGPL isn't here: each AGPL tool
# needs a review.
OPEN_SOURCE: Final[frozenset[str]] = frozenset(
    {"0BSD", "Apache-2.0", "BlueOak-1.0.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0", "CNRI-Python", "GPL-3.0-only", "GPL-3.0-or-later", "ISC", "MIT", "MPL-2.0", "PSF-2.0"},
)
# The same, for a Python package with no SPDX expression, which has these instead.
CLASSIFIER: Final[str] = "License :: OSI Approved :: "
OPEN_SOURCE_CLASSIFIERS: Final[frozenset[str]] = frozenset(
    {
        f"{CLASSIFIER}Apache Software License",
        f"{CLASSIFIER}BSD License",
        f"{CLASSIFIER}MIT License",
        f"{CLASSIFIER}Mozilla Public License 2.0 (MPL 2.0)",
        f"{CLASSIFIER}Python Software Foundation License",
    },
)

# The Node tools jetstream installs (astro check and Lighthouse CI), from its own lockfiles, by folder.
NODE_LOCKFILES: Final[dict[str, dict[str, Any]]] = {path.parent.name: json.loads(path.read_text()) for path in sorted((ROOT / "src" / "jetstream" / "node").glob("*/package-lock.json"))}


def installed_tools() -> list[NormalizedName]:
    """Return every package jetstream installs, with every pack's extra: jetstream itself, its dependencies and theirs."""
    extras: list[str] = importlib.metadata.metadata(DISTRIBUTION).get_all("Provides-Extra") or []
    found: set[NormalizedName] = set()
    todo: list[tuple[str, set[str]]] = [(DISTRIBUTION, set(extras))]
    while todo:
        name, wanted = todo.pop()
        if canonicalize_name(name) in found:
            continue
        found.add(canonicalize_name(name))
        for line in importlib.metadata.requires(name) or []:
            requirement: Requirement = Requirement(line)
            if requirement.marker is None or any(requirement.marker.evaluate({"extra": extra}) for extra in wanted or {""}):
                todo.append((requirement.name, set(requirement.extras)))
    return sorted(found)


def is_open_source(license_id: str) -> bool:
    """Return whether the SPDX expression ``license_id`` can be met with open-source licenses."""
    return npm_licenses.allows(license_id, OPEN_SOURCE)


def declares_open_source(metadata: PackageMetadata | Message) -> bool:
    """Return whether a Python package's ``metadata`` declares an open-source license: in its License-Expression, or failing that all its license classifiers, or failing that its License."""
    expression: str | None = metadata.get("License-Expression")
    classifiers: set[str] = {line for line in metadata.get_all("Classifier") or [] if line.startswith("License :: ")}
    if not expression and classifiers:
        return classifiers <= OPEN_SOURCE_CLASSIFIERS
    return is_open_source(expression or metadata.get("License") or "")


@pytest.mark.parametrize("package", installed_tools())
def test_package_license_is_allowed(package: NormalizedName) -> None:
    """Every package the packs install has an allowed license in its metadata, or one reviewed by hand."""
    reviewed: str | None = RECORDS["reviewed"].get(package)
    allowed: bool = is_open_source(reviewed) if reviewed else declares_open_source(importlib.metadata.metadata(package))
    assert allowed, f"{package}: its license needs a review (OPEN_SOURCE, or dev-tool-licenses.toml)"


@pytest.mark.parametrize(("package", "license_id"), [*RECORDS["bundled"].items(), *RECORDS["reviewed"].items()])
def test_recorded_licenses_are_allowed_and_installed(package: str, license_id: str) -> None:
    """Every license recorded by hand is an allowed one, for a package the packs still install."""
    assert canonicalize_name(package) in installed_tools(), f"{package} isn't installed any more: remove it from dev-tool-licenses.toml"
    assert is_open_source(license_id), f"{package}: {license_id}"


@pytest.mark.parametrize("tool", sorted(BINARIES))
def test_binary_license_is_allowed(tool: str) -> None:
    """Every binary tool's recorded license is an allowed one (update-binary.py --check compares it with GitHub's)."""
    assert is_open_source(BINARIES[tool]["license"]), f"{tool}: {BINARIES[tool]['license']}"


@pytest.mark.parametrize(
    ("tool", "path"),
    # jetstream's own stubs (links to stubs/) are MIT, and aren't third-party
    sorted((tool, path) for tool, lockfile in NODE_LOCKFILES.items() for path, package in lockfile["packages"].items() if "node_modules/" in path and not package.get("link")),
)
def test_node_tool_license_is_open_source(tool: str, path: str) -> None:
    """Every package in jetstream's Node lockfiles has an open-source license, by its SPDX ID."""
    license_: object = NODE_LOCKFILES[tool]["packages"][path].get("license")
    assert isinstance(license_, str), f"{tool} {path}: no license"
    assert is_open_source(license_), f"{tool} {path}: license {license_!r} needs a review (OPEN_SOURCE)"


@pytest.mark.parametrize(
    ("license_id", "open_source"),
    [
        ("MIT", True),
        ("GPL-3.0-or-later", True),
        ("BlueOak-1.0.0", True),
        ("Apache-2.0 AND CNRI-Python", True),
        ("(MIT OR CC0-1.0)", True),
        ("FSL-1.1-Apache-2.0", False),
        ("BUSL-1.1", False),
        ("SSPL-1.0", False),
        ("Elastic-2.0", False),
        ("AGPL-3.0-only", False),
        ("MIT AND AGPL-3.0-only", False),
        ("Some Custom License", False),
        ("", False),
    ],
)
def test_is_open_source(license_id: str, *, open_source: bool) -> None:
    """A license is compared by ID, so a source-available one fails even with an open-source one in its name, as does AGPL, one not on the list, or none, even next to an allowed one."""
    assert is_open_source(license_id) is open_source


@pytest.mark.parametrize(
    ("fields", "open_source"),
    [
        ([("License-Expression", "MIT")], True),
        ([("License-Expression", "FSL-1.1-Apache-2.0")], False),
        ([("Classifier", f"{CLASSIFIER}MIT License"), ("Classifier", "Topic :: Utilities")], True),
        ([("Classifier", f"{CLASSIFIER}MIT License"), ("License", "The MIT License, in full")], True),
        ([("Classifier", f"{CLASSIFIER}MIT License"), ("Classifier", f"{CLASSIFIER}GNU Affero General Public License v3")], False),
        ([("Classifier", "License :: Other/Proprietary License"), ("License", "MIT")], False),
        ([("License-Expression", "FSL-1.1-Apache-2.0"), ("Classifier", f"{CLASSIFIER}Apache Software License")], False),
        ([("License", "Apache-2.0")], True),
        ([("License", "FSL-1.1-Apache-2.0")], False),
        ([("License", "Apache License, Version 2.0")], False),
        ([], False),
    ],
)
def test_declares_open_source(fields: list[tuple[str, str]], *, open_source: bool) -> None:
    """A package's SPDX expression decides, then all its license classifiers, then its License, which must be an SPDX expression."""
    metadata: Message = Message()
    for name, value in fields:
        metadata[name] = value
    assert declares_open_source(metadata) is open_source
