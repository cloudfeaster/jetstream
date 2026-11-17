"""Tests for bin/update-binary.py."""

import datetime
import importlib.machinery
import importlib.util
import types
from pathlib import Path
from typing import Any, Final

import pytest
import tomlkit

_spec: importlib.machinery.ModuleSpec | None = importlib.util.spec_from_file_location("update_binary", Path(__file__).parent.parent / "bin" / "update-binary.py")
assert _spec is not None
assert _spec.loader is not None
update_binary: types.ModuleType = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_binary)

NOW: Final[datetime.datetime] = datetime.datetime(2026, 11, 17, tzinfo=datetime.UTC)

PINS: Final[str] = """\
# A comment that must survive.

[tool]
repo = "owner/tool"
version = "1.0.0"
tag = "v{version}"
asset = "tool-{version}-{platform}.tar.gz"
member = "tool"
checksums = "SHA256SUMS"

[tool.platforms]
linux_x86_64 = { platform = "linux-amd64", sha256 = "old1" }
macosx_11_0_arm64 = { platform = "macos-arm64", sha256 = "old2" }
"""


def release(version: str, days_old: int, digests: bool = True) -> dict[str, Any]:
    return {
        "tag_name": f"v{version}",
        "published_at": (NOW - datetime.timedelta(days=days_old)).isoformat(),
        "assets": [
            {"name": f"tool-{version}-linux-amd64.tar.gz", "digest": "sha256:new1" if digests else None},
            {"name": f"tool-{version}-macos-arm64.tar.gz", "digest": "sha256:new2" if digests else None},
            {"name": "SHA256SUMS", "digest": "sha256:xxx", "browser_download_url": f"https://example.test/{version}/SHA256SUMS"},
        ],
    }


def sha256sums(version: str, linux: str = "new1", macos: str = "new2") -> str:
    return f"{linux}  tool-{version}-linux-amd64.tar.gz\n{macos} *dist/tool-{version}-macos-arm64.tar.gz\n"


@pytest.fixture
def downloads(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Release assets by URL; the checksums for 1.1.0 by default."""
    files: dict[str, str] = {"https://example.test/1.1.0/SHA256SUMS": sha256sums("1.1.0")}

    def fake_fetch_text(url: str) -> str:
        if url not in files:
            raise update_binary.UpdateError(f"{url}: 404 Not Found")
        return files[url]

    monkeypatch.setattr(update_binary, "fetch_text", fake_fetch_text)
    return files


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, downloads: dict[str, str]) -> dict[str, Any]:  # noqa: ARG001
    responses: dict[str, Any] = {}

    def fake_github_api(path: str) -> Any:  # noqa: ANN401
        if path not in responses:
            raise update_binary.UpdateError(f"GitHub API {path}: 404 Not Found")
        return responses[path]

    monkeypatch.setattr(update_binary, "github_api", fake_github_api)
    return responses


def test_update_to_latest_keeps_comments_and_format(api: dict[str, Any]) -> None:
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=8)
    pins: tomlkit.TOMLDocument = tomlkit.parse(PINS)

    assert update_binary.update(pins, "tool", None, NOW) == "tool: 1.0.0 -> 1.1.0"
    assert tomlkit.dumps(pins) == (
        PINS.replace('version = "1.0.0"', 'version = "1.1.0"').replace("old1", "new1").replace("old2", "new2")
    )


def test_update_to_latest_respects_the_cooldown(api: dict[str, Any]) -> None:
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=3)
    with pytest.raises(update_binary.UpdateError, match="under 7 days ago"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_to_a_named_version_skips_the_cooldown(api: dict[str, Any]) -> None:
    api["repos/owner/tool/releases/tags/v1.1.0"] = release("1.1.0", days_old=0)
    pins: tomlkit.TOMLDocument = tomlkit.parse(PINS)
    assert update_binary.update(pins, "tool", "1.1.0", NOW) == "tool: 1.0.0 -> 1.1.0"
    assert pins["tool"]["platforms"]["linux_x86_64"]["sha256"] == "new1"


def test_update_fails_on_a_missing_asset(api: dict[str, Any]) -> None:
    rel: dict[str, Any] = release("1.1.0", days_old=8)
    rel["assets"] = rel["assets"][1:]
    api["repos/owner/tool/releases/latest"] = rel
    with pytest.raises(update_binary.UpdateError, match="has no asset tool-1.1.0-linux-amd64.tar.gz"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_fails_without_a_digest(api: dict[str, Any]) -> None:
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=8, digests=False)
    with pytest.raises(update_binary.UpdateError, match="no SHA-256 digest"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_fails_when_the_projects_checksum_differs(api: dict[str, Any], downloads: dict[str, str]) -> None:
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=8)
    downloads["https://example.test/1.1.0/SHA256SUMS"] = sha256sums("1.1.0", macos="other")
    with pytest.raises(update_binary.UpdateError, match="GitHub's digest new2 doesn't match other in SHA256SUMS"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_fails_when_the_checksums_file_has_no_entry(api: dict[str, Any], downloads: dict[str, str]) -> None:
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=8)
    downloads["https://example.test/1.1.0/SHA256SUMS"] = "new1  tool-1.1.0-linux-amd64.tar.gz\n"
    with pytest.raises(update_binary.UpdateError, match="SHA256SUMS in release v1.1.0 has no entry for tool-1.1.0-macos-arm64"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_fails_without_a_checksums_file(api: dict[str, Any]) -> None:
    rel: dict[str, Any] = release("1.1.0", days_old=8)
    rel["assets"] = rel["assets"][:2]
    api["repos/owner/tool/releases/latest"] = rel
    with pytest.raises(update_binary.UpdateError, match="has no checksums file SHA256SUMS"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_with_a_checksums_file_per_asset(api: dict[str, Any], downloads: dict[str, str]) -> None:
    rel: dict[str, Any] = release("1.1.0", days_old=8)
    rel["assets"] = rel["assets"][:2]
    for asset, sha256 in [("tool-1.1.0-linux-amd64.tar.gz", "new1"), ("tool-1.1.0-macos-arm64.tar.gz", "new2")]:
        url: str = f"https://example.test/{asset}.sha256"
        rel["assets"].append({"name": f"{asset}.sha256", "browser_download_url": url})
        downloads[url] = f"{sha256}  {asset}\n"
    api["repos/owner/tool/releases/latest"] = rel
    pins: tomlkit.TOMLDocument = tomlkit.parse(PINS.replace('"SHA256SUMS"', '"{asset}.sha256"'))
    assert update_binary.update(pins, "tool", None, NOW) == "tool: 1.0.0 -> 1.1.0"


def test_parse_checksums() -> None:
    assert update_binary.parse_checksums("ABC  a.tar.gz\ndef *dir/b.tar.gz\n\nnot-a-line\n") == {
        "a.tar.gz": "abc",
        "b.tar.gz": "def",
    }


def test_update_fails_on_unknown_tool(api: dict[str, Any]) -> None:  # noqa: ARG001
    with pytest.raises(update_binary.UpdateError, match="no tool nope"):
        update_binary.update(tomlkit.parse(PINS), "nope", None, NOW)


@pytest.mark.parametrize(
    ("latest", "days_old", "stale"),
    [
        ("1.0.0", 30, False),
        ("1.1.0", 3, False),  # still in the cooldown
        ("1.1.0", 8, True),
    ],
)
def test_check(api: dict[str, Any], latest: str, days_old: int, stale: bool) -> None:
    api["repos/owner/tool/releases/latest"] = release(latest, days_old)
    assert bool(update_binary.check(tomlkit.parse(PINS), NOW)) == stale


def test_version_from_tag() -> None:
    assert update_binary.version_from_tag("v{version}", "v1.2.3") == "1.2.3"
    assert update_binary.version_from_tag("{version}", "1.2.3") == "1.2.3"
    with pytest.raises(update_binary.UpdateError):
        update_binary.version_from_tag("v{version}", "release-1.2.3")
