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
        ("MIT-0", True),
        ("PSF-2.0", True),
        ("OFL-1.1", True),
        ("OFL-1.0", False),
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
    """Return a package-lock.json with ``direct`` as the root's dependencies, packages/* as its workspaces, and ``packages`` under node_modules/."""
    return {"lockfileVersion": 3, "packages": {"": {"workspaces": ["packages/*"], "dependencies": direct}} | {f"node_modules/{name}": package for name, package in packages.items()}}


def test_mpl_is_allowed_only_in_a_transitive_dependency() -> None:
    """MPL-2.0 is allowed when another package needs it, not as one of the site's own dependencies (licensing.md)."""
    transitive: dict[str, Any] = lockfile({"a": "1.0.0"}, {"a": {"version": "1.0.0", "license": "MIT"}, "b": {"version": "2.0.0", "license": "MPL-2.0"}})
    assert npm_licenses.failures(transitive) == []
    direct: dict[str, Any] = lockfile({"b": "2.0.0"}, {"b": {"version": "2.0.0", "license": "MPL-2.0"}})
    assert npm_licenses.failures(direct) == ["node_modules/b 2.0.0: MPL-2.0 isn't allowed in a direct product dependency"]


def test_only_product_dependencies_are_checked() -> None:
    """Dev dependencies and the repo's own workspace packages are skipped; an optional product dependency isn't."""
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


@pytest.mark.parametrize("folder", ["../vendor", "vendor", "packages/a/vendor"])
@pytest.mark.parametrize(("license_", "allowed"), [("GPL-3.0-only", False), ("MPL-2.0", False), ("MIT", True)])
def test_a_file_dependency_is_checked(folder: str, license_: str, *, allowed: bool) -> None:
    """A ``file:`` dependency on a folder that isn't a workspace, outside the repo or in it, is a direct dependency, with its license on the folder's entry."""
    data: dict[str, Any] = lockfile({"a": f"file:{folder}"}, {"a": {"resolved": folder, "link": True}})
    data["packages"][folder] = {"name": "a", "version": "1.0.0", "license": license_}
    assert npm_licenses.failures(data) == ([] if allowed else [f"{folder} 1.0.0: {license_} isn't allowed in a direct product dependency"])


def test_a_dev_file_dependency_is_not_checked() -> None:
    """A ``file:`` dev dependency is a development tool; npm marks the folder's entry as dev."""
    data: dict[str, Any] = lockfile({}, {"a": {"resolved": "../vendor", "link": True}})
    data["packages"]["../vendor"] = {"name": "a", "version": "1.0.0", "license": "GPL-3.0-only", "dev": True}
    assert npm_licenses.failures(data) == []


def test_a_file_dependencys_own_dependency_is_transitive() -> None:
    """What a ``file:`` dependency needs is transitive, so MPL-2.0 is allowed in it, and GPL isn't."""
    data: dict[str, Any] = lockfile({"a": "file:vendor"}, {"a": {"resolved": "vendor", "link": True}})
    data["packages"]["vendor"] = {"name": "a", "version": "1.0.0", "license": "MIT", "dependencies": {"b": "1.0.0", "c": "1.0.0"}}
    data["packages"]["vendor/node_modules/b"] = {"version": "1.0.0", "license": "MPL-2.0"}
    data["packages"]["vendor/node_modules/c"] = {"version": "1.0.0", "license": "GPL-3.0-only"}
    assert npm_licenses.failures(data) == ["vendor/node_modules/c 1.0.0: GPL-3.0-only isn't allowed in a transitive product dependency"]


@pytest.mark.parametrize(
    ("path", "workspaces", "own"),
    [
        ("", [], True),
        ("site", ["site"], True),
        ("site", ["./site/"], True),
        ("packages/a", ["packages/*"], True),
        ("packages/a/b", ["packages/*"], False),
        ("packages/a/b", ["packages/**"], True),
        ("packages/a", ["packages/*", "!packages/a"], False),
        ("packages/a", ["!packages/a", "packages/*"], True),
        ("packages/a", [], False),
        ("../vendor", ["**"], False),
        ("node_modules/a", ["**"], False),
        ("packages/a/node_modules/b", ["packages/**"], False),
    ],
)
def test_is_own(path: str, workspaces: list[str], own: bool) -> None:  # noqa: FBT001 (a parametrized case)
    """The repo's own packages are the root and those its workspaces patterns match, the last match deciding, and never one outside the repo or in node_modules/."""
    assert npm_licenses.is_own(path, workspaces) is own


def test_workspaces_can_be_an_object() -> None:
    """The root's workspaces can be ``{"packages": [...]}`` too."""
    data: dict[str, Any] = lockfile({"a": "*"}, {"a": {"resolved": "packages/a", "link": True}})
    data["packages"][""]["workspaces"] = {"packages": ["packages/*"]}
    data["packages"]["packages/a"] = {"version": "1.0.0"}
    assert npm_licenses.failures(data) == []


@pytest.mark.parametrize(
    ("installed", "path"),
    [(False, "node_modules/b"), (True, "packages/site/node_modules/b")],
    ids=["hoisted", "nested"],
)
def test_a_workspaces_own_dependency_is_direct(installed: bool, path: str) -> None:  # noqa: FBT001 (a parametrized case)
    """A dependency that one of the repo's workspace packages declares is direct, where npm installed it, so MPL-2.0 isn't allowed in it."""
    data: dict[str, Any] = lockfile({"b": "1.0.0"} if installed else {}, {"b": {"version": "1.0.0", "license": "MIT"}})
    data["packages"]["packages/site"] = {"version": "1.0.0", "dependencies": {"b": "2.0.0"}}
    data["packages"][path] = {"version": "2.0.0", "license": "MPL-2.0"}
    assert npm_licenses.failures(data) == [f"{path} 2.0.0: MPL-2.0 isn't allowed in a direct product dependency"]


def test_a_nested_copy_only_another_package_needs_is_transitive() -> None:
    """A copy of a package nested under another dependency is that dependency's, so it's transitive, even when the root declares the package too."""
    data: dict[str, Any] = lockfile({"a": "1.0.0", "b": "1.0.0"}, {"a": {"version": "1.0.0", "license": "MIT"}, "b": {"version": "1.0.0", "license": "MIT"}})
    data["packages"]["node_modules/a/node_modules/b"] = {"version": "2.0.0", "license": "MPL-2.0"}
    assert npm_licenses.failures(data) == []


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
