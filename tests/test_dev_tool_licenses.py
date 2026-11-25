"""Every tool jetstream installs has a license licensing.md allows for a development tool.

That's any open-source license, GPL, LGPL and AGPL included, except that an
AGPL tool needs a review first. So a license licensecheck can't recognise, a
missing one, or an AGPL one fails until it's reviewed and recorded in
dev-tool-licenses.toml's [reviewed]. The product rule, which the python pack's
licensecheck hook applies to a repo's own dependencies, is a different one.
"""

import importlib.metadata
import json
import tomllib
from pathlib import Path
from typing import Any, Final

import pytest
from licensecheck.license_matrix import licenseType
from licensecheck.models.license import License
from licensecheck.models.packageinfo import PackageInfo
from licensecheck.packageinforesolver import LocalPackageInfo, normalize_license
from packaging.requirements import Requirement
from packaging.utils import NormalizedName, canonicalize_name

from jetstream import npm_licenses

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DISTRIBUTION: Final[str] = "cloudfeaster-jetstream"
RECORDS: Final[dict[str, Any]] = tomllib.loads((ROOT / "dev-tool-licenses.toml").read_text())
BINARIES: Final[dict[str, Any]] = tomllib.loads((ROOT / "binaries.toml").read_text())
NOT_ALLOWED: Final[frozenset[License]] = frozenset({License.AGPL_3_PLUS, License.PROPRIETARY, License.UNKNOWN, License.NO_LICENSE})
# licensecheck reads an SPDX AGPL ID, such as AGPL-3.0-only, as the GPL it contains, so these are looked for first.
AGPL: Final[tuple[str, ...]] = ("AGPL", "AFFERO")


# The Node tools jetstream installs (astro check and Lighthouse CI), from its own lockfiles, by folder.
NODE_LOCKFILES: Final[dict[str, dict[str, Any]]] = {path.parent.name: json.loads(path.read_text()) for path in sorted((ROOT / "src" / "jetstream" / "node").glob("*/package-lock.json"))}
# The SPDX IDs in those lockfiles that are open-source licenses. Their packages
# are compared by ID, not with licensecheck, which reads FSL-1.1-Apache-2.0
# (source-available, not open source) as Apache and doesn't know BlueOak. A
# new ID fails until it's reviewed and added here, or, if it isn't open
# source, the package is stubbed out (src/jetstream/node/lighthouse/stubs/).
NODE_OPEN_SOURCE: Final[frozenset[str]] = frozenset(
    {"0BSD", "Apache-2.0", "BlueOak-1.0.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0", "ISC", "MIT", "MPL-2.0", "PSF-2.0"},
)


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


def not_allowed(license_text: str) -> set[License]:
    """Return the licenses in ``license_text`` that a development tool can't have without a review."""
    if not license_text.strip():
        return {License.NO_LICENSE}
    if any(word in license_text.upper() for word in AGPL):
        return {License.AGPL_3_PLUS}
    return licenseType(normalize_license(license_text)) & NOT_ALLOWED


@pytest.mark.parametrize("package", installed_tools())
def test_package_license_is_allowed(package: NormalizedName) -> None:
    """Every package the packs install has an allowed license in its metadata, or one reviewed by hand."""
    reviewed: str | None = RECORDS["reviewed"].get(package)
    found: str = reviewed or str(LocalPackageInfo(PackageInfo(name=package)).get_license() or "")
    assert not not_allowed(found), f"{package}: license {found!r} needs a review (dev-tool-licenses.toml)"


@pytest.mark.parametrize(("package", "license_id"), [*RECORDS["bundled"].items(), *RECORDS["reviewed"].items()])
def test_recorded_licenses_are_allowed_and_installed(package: str, license_id: str) -> None:
    """Every license recorded by hand is an allowed one, for a package the packs still install."""
    assert canonicalize_name(package) in installed_tools(), f"{package} isn't installed any more: remove it from dev-tool-licenses.toml"
    assert not not_allowed(license_id), f"{package}: {license_id}"


@pytest.mark.parametrize("tool", sorted(BINARIES))
def test_binary_license_is_allowed(tool: str) -> None:
    """Every binary tool's recorded license is an allowed one (update-binary.py --check compares it with GitHub's)."""
    assert not not_allowed(BINARIES[tool]["license"]), f"{tool}: {BINARIES[tool]['license']}"


@pytest.mark.parametrize(
    ("tool", "path"),
    # jetstream's own stubs (links to stubs/) are MIT, and aren't third-party
    sorted((tool, path) for tool, lockfile in NODE_LOCKFILES.items() for path, package in lockfile["packages"].items() if "node_modules/" in path and not package.get("link")),
)
def test_node_tool_license_is_open_source(tool: str, path: str) -> None:
    """Every package in jetstream's Node lockfiles has an open-source license, by its SPDX ID."""
    license_: object = NODE_LOCKFILES[tool]["packages"][path].get("license")
    assert isinstance(license_, str), f"{tool} {path}: no license"
    assert npm_licenses.allows(license_, NODE_OPEN_SOURCE), f"{tool} {path}: license {license_!r} needs a review (NODE_OPEN_SOURCE)"


@pytest.mark.parametrize(("license_id", "open_source"), [("FSL-1.1-Apache-2.0", False), ("BUSL-1.1", False), ("BlueOak-1.0.0", True), ("(MIT OR CC0-1.0)", True)])
def test_node_licenses_are_compared_by_id(license_id: str, *, open_source: bool) -> None:
    """A source-available license fails even with an open-source one in its name, and an open-source one licensecheck doesn't know passes."""
    assert npm_licenses.allows(license_id, NODE_OPEN_SOURCE) is open_source


@pytest.mark.parametrize(
    ("license_text", "allowed"),
    [
        ("MIT", True),
        ("Apache-2.0 AND CNRI-Python", True),
        ("GPL-3.0-or-later", True),
        ("Mozilla Public License 2.0 (MPL 2.0)", True),
        ("AGPL-3.0-only", False),
        ("MIT AND AGPL-3.0-only", False),
        ("Some Custom License", False),
        ("", False),
    ],
)
def test_not_allowed(license_text: str, *, allowed: bool) -> None:
    """Any open-source license is allowed, but not AGPL, an unrecognised one, or none, even next to an allowed one."""
    assert (not not_allowed(license_text)) == allowed
