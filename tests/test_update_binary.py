"""Tests for bin/update-binary.py."""

import datetime
import importlib.machinery
import importlib.util
import types
from pathlib import Path
from typing import Any

import pytest
import tomlkit

_spec: importlib.machinery.ModuleSpec | None = importlib.util.spec_from_file_location("update_binary", Path(__file__).parent.parent / "bin" / "update-binary.py")
assert _spec is not None
assert _spec.loader is not None
update_binary: types.ModuleType = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_binary)

NOW = datetime.datetime(2026, 11, 17, tzinfo=datetime.UTC)

PINS = """\
# A comment that must survive.

[tool]
repo = "owner/tool"
version = "1.0.0"
tag = "v{version}"
asset = "tool-{version}-{platform}.tar.gz"
member = "tool"

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
            {"name": "checksums.txt", "digest": "sha256:xxx"},
        ],
    }


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
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
