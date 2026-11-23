"""Tests for jetstream.npm_licenses, the website pack's npm license check."""

import json
from pathlib import Path
from typing import Any

import pytest

from jetstream import npm_licenses


@pytest.mark.parametrize(
    ("expression", "allowed"),
    [
        ("MIT", True),
        ("ISC", True),
        ("0BSD", True),
        ("GPL-3.0-only", False),
        ("(MIT OR GPL-3.0-only)", True),
        ("GPL-3.0-only OR MIT", True),
        ("MIT AND ISC", True),
        ("MIT AND GPL-3.0-only", False),
        ("(MIT OR Apache-2.0) AND BSD-3-Clause", True),
        ("(GPL-2.0-only OR LGPL-3.0-only) AND MIT", False),
        ("Apache-2.0 WITH LLVM-exception", False),
        ("MIT OR (Apache-2.0 WITH LLVM-exception)", True),
        ("SEE LICENSE IN LICENSE.md", False),
        ("(MIT", False),
        ("", False),
        ("MIT OR", False),
        ("MIT OR (GPL-3.0-only", False),
        ("MIT OR )", False),
        ("MIT AND", False),
        ("OR MIT", False),
        ("MIT GPL-3.0-only", False),
        ("MIT OR (Apache-2.0 WITH)", False),
    ],
)
def test_allows_reads_spdx_expressions(expression: str, allowed: bool) -> None:  # noqa: FBT001 (a parametrized case)
    """An OR needs one side allowed, an AND both; anything that isn't a plain allowed license, a WITH exception included, isn't, nor is a malformed expression, even with an allowed license in it."""
    assert npm_licenses.allows(expression, npm_licenses.ALLOWED) is allowed


def lockfile(direct: dict[str, str], packages: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return a package-lock.json with ``direct`` as the root's dependencies and ``packages`` under node_modules/."""
    return {"lockfileVersion": 3, "packages": {"": {"dependencies": direct}} | {f"node_modules/{name}": package for name, package in packages.items()}}


def test_mpl_is_allowed_only_in_a_transitive_dependency() -> None:
    """MPL-2.0 is allowed when another package needs it, not as one of the site's own dependencies (licensing.md)."""
    transitive: dict[str, Any] = lockfile({"a": "1.0.0"}, {"a": {"version": "1.0.0", "license": "MIT"}, "b": {"version": "2.0.0", "license": "MPL-2.0"}})
    assert npm_licenses.failures(transitive) == []
    direct: dict[str, Any] = lockfile({"b": "2.0.0"}, {"b": {"version": "2.0.0", "license": "MPL-2.0"}})
    assert npm_licenses.failures(direct) == ["node_modules/b 2.0.0: MPL-2.0 isn't allowed in a direct product dependency"]


def test_only_product_dependencies_are_checked() -> None:
    """Dev dependencies, links and the repo's own workspace packages are skipped; an optional product dependency isn't."""
    data: dict[str, Any] = lockfile(
        {},
        {
            "dev-tool": {"version": "1.0.0", "license": "GPL-3.0-only", "dev": True},
            "linked": {"resolved": "packages/linked", "link": True},
            "optional": {"version": "1.0.0", "license": "LGPL-3.0-or-later", "optional": True},
        },
    )
    data["packages"]["packages/linked"] = {"version": "1.0.0", "license": "UNLICENSED"}
    assert npm_licenses.failures(data) == ["node_modules/optional 1.0.0: LGPL-3.0-or-later isn't allowed in a transitive product dependency"]


def test_a_workspaces_own_dependency_is_direct() -> None:
    """A dependency that one of the repo's workspace packages declares is direct, like one the root declares, so MPL-2.0 isn't allowed in it."""
    data: dict[str, Any] = lockfile({}, {"b": {"version": "2.0.0", "license": "MPL-2.0"}})
    data["packages"]["packages/site"] = {"version": "1.0.0", "dependencies": {"b": "2.0.0"}}
    assert npm_licenses.failures(data) == ["node_modules/b 2.0.0: MPL-2.0 isn't allowed in a direct product dependency"]


@pytest.mark.parametrize("license_", [None, ["MIT"]], ids=["missing", "not-a-string"])
def test_a_missing_or_unreadable_license_fails(license_: object) -> None:
    """A package with no license, or one npm didn't write as an SPDX expression, fails."""
    package: dict[str, Any] = {"version": "1.0.0"} | ({} if license_ is None else {"license": license_})
    assert npm_licenses.failures(lockfile({"a": "1.0.0"}, {"a": package})) == [f"node_modules/a 1.0.0: {license_ or 'no license'} isn't allowed in a direct product dependency"]


def test_main_prints_each_failure_and_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The module's main reads the lockfile it's given, prints each failure, and returns 1 if there are any, 0 if not."""
    path: Path = tmp_path / "package-lock.json"
    path.write_text(json.dumps(lockfile({"a": "1.0.0"}, {"a": {"version": "1.0.0", "license": "GPL-3.0-only"}})))
    assert npm_licenses.main([str(path)]) == 1
    assert capsys.readouterr().out == "node_modules/a 1.0.0: GPL-3.0-only isn't allowed in a direct product dependency\n"
    path.write_text(json.dumps(lockfile({}, {})))
    assert npm_licenses.main([str(path)]) == 0


def test_main_rejects_a_lockfile_with_no_packages_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A lockfile from npm 6 or older, with no packages table, can't be checked, so it fails (exit 2) rather than passing."""
    path: Path = tmp_path / "package-lock.json"
    path.write_text(json.dumps({"lockfileVersion": 1, "dependencies": {"a": {"version": "1.0.0"}}}))
    assert npm_licenses.main([str(path)]) == 2  # noqa: PLR2004 (main's exit code for a lockfile it can't check)
    assert "no packages table" in capsys.readouterr().err
