"""Tests for bin/update-binary.py."""

import datetime as dt
import email.message
import importlib.machinery
import importlib.util
import io
import types
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final, NoReturn

import pytest
import tomlkit

_spec: importlib.machinery.ModuleSpec | None = importlib.util.spec_from_file_location("update_binary", Path(__file__).parent.parent / "bin" / "update-binary.py")
assert _spec is not None
assert _spec.loader is not None
update_binary: types.ModuleType = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_binary)

# The real fetch_text, before the autouse downloads fixture fakes it.
FETCH_TEXT: Final[Callable[[str], str]] = update_binary.fetch_text

NOW: Final[dt.datetime] = dt.datetime(2026, 11, 17, tzinfo=dt.UTC)

PINS: Final[str] = """\
# A comment that must survive.

[tool]
repo = "owner/tool"
license = "MIT"
version = "1.0.0"
tag = "v{version}"
asset = "tool-{version}-{platform}.tar.gz"
member = "tool"
checksums = "SHA256SUMS"

[tool.platforms]
linux_x86_64 = { platform = "linux-amd64", sha256 = "old1" }
macosx_11_0_arm64 = { platform = "macos-arm64", sha256 = "old2" }
"""


def release(version: str, days_old: int, *, digests: bool = True) -> dict[str, Any]:
    """Return a GitHub release of tool ``version``, published ``days_old`` days before NOW."""
    return {
        "tag_name": f"v{version}",
        "published_at": (NOW - dt.timedelta(days=days_old)).isoformat(),
        "assets": [
            {"name": f"tool-{version}-linux-amd64.tar.gz", "digest": "sha256:new1" if digests else None},
            {"name": f"tool-{version}-macos-arm64.tar.gz", "digest": "sha256:new2" if digests else None},
            {"name": "SHA256SUMS", "digest": "sha256:xxx"},
        ],
    }


def sha256sums(version: str, linux: str = "new1", macos: str = "new2") -> str:
    """Return a checksums file for ``version``'s assets, in both of sha256sum's formats."""
    return f"{linux}  tool-{version}-linux-amd64.tar.gz\n{macos} *dist/tool-{version}-macos-arm64.tar.gz\n"


@pytest.fixture(autouse=True)
def downloads(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Return release assets by their URL after https://github.com/; the checksums for 1.1.0 by default."""
    files: dict[str, str] = {"owner/tool/releases/download/v1.1.0/SHA256SUMS": sha256sums("1.1.0")}

    def fake_fetch_text(path: str) -> str:
        if path not in files:
            msg: str = f"https://github.com/{path}: 404 Not Found"
            raise update_binary.UpdateError(msg)
        return files[path]

    monkeypatch.setattr(update_binary, "fetch_text", fake_fetch_text)
    return files


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Return GitHub API responses by path, faked, with a 404 for any other path; each test repo is MIT."""
    responses: dict[str, Any] = {f"repos/owner/{repo}": {"license": {"spdx_id": "MIT"}} for repo in ("tool", "other")}

    def fake_github_api(path: str) -> dict[str, Any]:
        if path not in responses:
            msg: str = f"GitHub API {path}: 404 Not Found"
            raise update_binary.UpdateError(msg)
        return responses[path]

    monkeypatch.setattr(update_binary, "github_api", fake_github_api)
    return responses


def test_update_to_latest_keeps_comments_and_format(api: dict[str, Any]) -> None:
    """Updating changes only the version and SHA-256s, keeping comments and layout."""
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=8)
    pins: tomlkit.TOMLDocument = tomlkit.parse(PINS)

    assert update_binary.update(pins, "tool", None, NOW) == "tool: 1.0.0 -> 1.1.0"
    assert tomlkit.dumps(pins) == (PINS.replace('version = "1.0.0"', 'version = "1.1.0"').replace("old1", "new1").replace("old2", "new2"))


def test_update_to_latest_respects_the_cooldown(api: dict[str, Any]) -> None:
    """A latest release under 7 days old isn't taken."""
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=3)
    with pytest.raises(update_binary.UpdateError, match="under 7 days ago"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_to_a_named_version_skips_the_cooldown(api: dict[str, Any]) -> None:
    """A version named on the command line is pinned however new it is."""
    api["repos/owner/tool/releases/tags/v1.1.0"] = release("1.1.0", days_old=0)
    pins: tomlkit.TOMLDocument = tomlkit.parse(PINS)
    assert update_binary.update(pins, "tool", "1.1.0", NOW) == "tool: 1.0.0 -> 1.1.0"
    assert pins["tool"]["platforms"]["linux_x86_64"]["sha256"] == "new1"


def test_update_fails_on_a_missing_asset(api: dict[str, Any]) -> None:
    """A release without a pinned platform's asset is an error."""
    rel: dict[str, Any] = release("1.1.0", days_old=8)
    rel["assets"] = rel["assets"][1:]
    api["repos/owner/tool/releases/latest"] = rel
    with pytest.raises(update_binary.UpdateError, match=r"has no asset tool-1.1.0-linux-amd64.tar.gz"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_fails_without_a_digest(api: dict[str, Any]) -> None:
    """A release whose assets have no GitHub SHA-256 digest is an error."""
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=8, digests=False)
    with pytest.raises(update_binary.UpdateError, match="no SHA-256 digest"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_fails_when_the_projects_checksum_differs(api: dict[str, Any], downloads: dict[str, str]) -> None:
    """GitHub's digest must match the project's own checksums file."""
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=8)
    downloads["owner/tool/releases/download/v1.1.0/SHA256SUMS"] = sha256sums("1.1.0", macos="other")
    with pytest.raises(update_binary.UpdateError, match="GitHub's digest new2 doesn't match other in SHA256SUMS"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_fails_when_the_checksums_file_has_no_entry(api: dict[str, Any], downloads: dict[str, str]) -> None:
    """A checksums file must list every pinned asset."""
    api["repos/owner/tool/releases/latest"] = release("1.1.0", days_old=8)
    downloads["owner/tool/releases/download/v1.1.0/SHA256SUMS"] = "new1  tool-1.1.0-linux-amd64.tar.gz\n"
    with pytest.raises(update_binary.UpdateError, match=r"SHA256SUMS in release v1.1.0 has no entry for tool-1.1.0-macos-arm64"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_fails_without_a_checksums_file(api: dict[str, Any]) -> None:
    """A release without the pinned checksums file is an error."""
    rel: dict[str, Any] = release("1.1.0", days_old=8)
    rel["assets"] = rel["assets"][:2]
    api["repos/owner/tool/releases/latest"] = rel
    with pytest.raises(update_binary.UpdateError, match="has no checksums file SHA256SUMS"):
        update_binary.update(tomlkit.parse(PINS), "tool", None, NOW)


def test_update_with_a_checksums_file_per_asset(api: dict[str, Any], downloads: dict[str, str]) -> None:
    """A checksums template naming ``{asset}`` reads one checksums file per asset."""
    rel: dict[str, Any] = release("1.1.0", days_old=8)
    rel["assets"] = rel["assets"][:2]
    for asset, sha256 in [("tool-1.1.0-linux-amd64.tar.gz", "new1"), ("tool-1.1.0-macos-arm64.tar.gz", "new2")]:
        rel["assets"].append({"name": f"{asset}.sha256"})
        downloads[f"owner/tool/releases/download/v1.1.0/{asset}.sha256"] = f"{sha256}  {asset}\n"
    api["repos/owner/tool/releases/latest"] = rel
    pins: tomlkit.TOMLDocument = tomlkit.parse(PINS.replace('"SHA256SUMS"', '"{asset}.sha256"'))
    assert update_binary.update(pins, "tool", None, NOW) == "tool: 1.0.0 -> 1.1.0"


def test_fetch_text_gets_the_asset_from_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """A release asset is fetched from https://github.com/, by its path there."""
    requested: list[str] = []

    def fake_urlopen(url: str, **_kwargs: object) -> io.BytesIO:
        requested.append(url)
        return io.BytesIO(b"abc  tool.tar.gz\n")

    monkeypatch.setattr(update_binary.urllib.request, "urlopen", fake_urlopen)
    assert FETCH_TEXT("owner/tool/releases/download/v1.0.0/SHA256SUMS") == "abc  tool.tar.gz\n"
    assert requested == ["https://github.com/owner/tool/releases/download/v1.0.0/SHA256SUMS"]


def test_parse_checksums() -> None:
    """Text and binary-mode lines are read, hashes are lower-cased, paths are reduced to file names, and other lines are skipped."""
    assert update_binary.parse_checksums("ABC  a.tar.gz\ndef *dir/b.tar.gz\n\nnot-a-line\n") == {
        "a.tar.gz": "abc",
        "b.tar.gz": "def",
    }


@pytest.mark.usefixtures("api")
def test_update_fails_on_unknown_tool() -> None:
    """Naming a tool that isn't in binaries.toml is an error."""
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
def test_check(api: dict[str, Any], latest: str, days_old: int, *, stale: bool) -> None:
    """A pin is stale only when a newer release is past the cooldown."""
    api["repos/owner/tool/releases/latest"] = release(latest, days_old)
    assert bool(update_binary.check(tomlkit.parse(PINS), NOW)) == stale


@pytest.mark.parametrize(
    ("latest", "days_old", "report"),
    [
        ("1.0.0", 30, "tool: pinned 1.0.0; latest 1.0.0 (2026-10-18): up to date"),
        ("1.1.0", 3, "tool: pinned 1.0.0; latest 1.1.0 (2026-11-14): in the cooldown until 2026-11-21, so 1.0.0 stays"),
        ("1.1.0", 8, "tool: pinned 1.0.0; latest 1.1.0 (2026-11-09): needs updating"),
    ],
)
def test_check_verbose_reports_each_tool(
    api: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    latest: str,
    days_old: int,
    report: str,
) -> None:
    """With verbose, each tool's pinned and latest versions are printed, with what that means."""
    api["repos/owner/tool/releases/latest"] = release(latest, days_old)
    update_binary.check(tomlkit.parse(PINS), NOW, verbose=True)
    assert capsys.readouterr().out == report + "\n"


def test_check_is_quiet_by_default(api: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    """Without verbose, check prints nothing."""
    api["repos/owner/tool/releases/latest"] = release("1.0.0", 30)
    update_binary.check(tomlkit.parse(PINS), NOW)
    assert capsys.readouterr().out == ""


def test_check_reports_every_tool_even_when_one_fails(api: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    """A tool that can't be checked is reported, and the other tools are still checked."""
    pins: str = PINS + PINS.replace("[tool", "[other").replace("owner/tool", "owner/other").split("\n", 2)[2]
    api["repos/owner/other/releases/latest"] = release("1.0.0", 30)  # owner/tool isn't there: a 404
    problems: list[str] = update_binary.check(tomlkit.parse(pins), NOW, verbose=True)
    assert problems == ["tool: couldn't check: GitHub API repos/owner/tool/releases/latest: 404 Not Found"]
    assert capsys.readouterr().out == ("tool: couldn't check: GitHub API repos/owner/tool/releases/latest: 404 Not Found\nother: pinned 1.0.0; latest 1.0.0 (2026-10-18): up to date\n")


@pytest.mark.parametrize(
    ("reported", "github_license", "problem"),
    [
        ("MIT", None, None),
        ("GPL-3.0", None, "tool: GitHub reports the license GPL-3.0, not MIT; review it, and update its license in binaries.toml"),
        (None, None, "tool: GitHub reports the license none, not MIT; review it, and update its license in binaries.toml"),
        ("NOASSERTION", "NOASSERTION", None),
        ("MIT", "NOASSERTION", "tool: GitHub reports the license MIT, not NOASSERTION; review it, and update its license in binaries.toml"),
    ],
)
def test_check_fails_when_the_license_changes(api: dict[str, Any], reported: str | None, github_license: str | None, problem: str | None) -> None:
    """--check fails when GitHub's license for a tool's repo isn't the one recorded, or its github-license where GitHub can't tell."""
    api["repos/owner/tool/releases/latest"] = release("1.0.0", 30)
    api["repos/owner/tool"] = {"license": {"spdx_id": reported} if reported else None}
    pins: tomlkit.TOMLDocument = tomlkit.parse(PINS)
    if github_license:
        pins["tool"]["github-license"] = github_license
    assert update_binary.check(pins, NOW) == ([problem] if problem else [])


def http_error(code: int, reason: str, body: bytes, headers: dict[str, str]) -> urllib.error.HTTPError:
    """Return an HTTPError from the GitHub API with ``body`` and ``headers``."""
    message: email.message.Message = email.message.Message()
    for name, value in headers.items():
        message[name] = value
    return urllib.error.HTTPError("https://api.github.com/x", code, reason, message, io.BytesIO(body))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            http_error(403, "Forbidden", b'{"message": "API rate limit exceeded for installation."}', {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1795395600"}),
            "GitHub API x: 403 Forbidden: API rate limit exceeded for installation. (rate limit: 0 requests left, resets 2026-11-23 01:00 UTC)",
        ),
        (
            http_error(403, "Forbidden", b'{"message": "You have exceeded a secondary rate limit."}', {"x-ratelimit-remaining": "990", "retry-after": "60"}),
            "GitHub API x: 403 Forbidden: You have exceeded a secondary rate limit. (rate limit: 990 requests left, retry after 60s)",
        ),
        (http_error(403, "Forbidden", b"<html>not JSON</html>", {}), "GitHub API x: 403 Forbidden"),
    ],
)
def test_github_api_errors_say_why(monkeypatch: pytest.MonkeyPatch, error: urllib.error.HTTPError, expected: str) -> None:
    """An API error adds GitHub's message and the rate-limit headers, and copes with a body that isn't JSON."""

    def refuse(*_args: object, **_kwargs: object) -> NoReturn:
        raise error

    monkeypatch.setattr(update_binary.urllib.request, "urlopen", refuse)
    with pytest.raises(update_binary.UpdateError) as raised:
        update_binary.github_api("x")
    assert str(raised.value) == expected


IP_ALLOW_LIST: Final[bytes] = b'{"message": "Although you appear to have the correct authorization credentials, the `owner` organization has an IP allow list enabled, and your IP address is not permitted to access this resource."}'


@pytest.mark.parametrize(
    ("body", "retried"),
    [
        (IP_ALLOW_LIST, True),
        (b'{"message": "API rate limit exceeded for installation."}', False),
    ],
)
def test_github_api_retries_without_the_token_only_for_an_ip_allow_list(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: bytes,
    *,
    retried: bool,
) -> None:
    """Only an IP allow list refusal is retried without GITHUB_TOKEN; other 403s fail."""
    monkeypatch.setenv("GITHUB_TOKEN", "a-token")
    sent: list[str | None] = []  # each request's Authorization header

    def fake_urlopen(request: urllib.request.Request, **_kwargs: object) -> io.BytesIO:
        sent.append(request.get_header("Authorization"))
        if request.has_header("Authorization"):
            raise http_error(403, "Forbidden", body, {"x-ratelimit-remaining": "4976"})
        return io.BytesIO(b'{"tag_name": "v1.0.0"}')

    monkeypatch.setattr(update_binary.urllib.request, "urlopen", fake_urlopen)
    if retried:
        assert update_binary.github_api("x") == {"tag_name": "v1.0.0"}
        assert sent == ["Bearer a-token", None]
        assert "retrying without GITHUB_TOKEN" in capsys.readouterr().err
    else:
        with pytest.raises(update_binary.UpdateError, match="rate limit exceeded"):
            update_binary.github_api("x")
        assert sent == ["Bearer a-token"]


def test_version_from_tag() -> None:
    """The version is read from a tag using the pin's template, and a tag that doesn't match is an error."""
    assert update_binary.version_from_tag("v{version}", "v1.2.3") == "1.2.3"
    assert update_binary.version_from_tag("{version}", "1.2.3") == "1.2.3"
    with pytest.raises(update_binary.UpdateError):
        update_binary.version_from_tag("v{version}", "release-1.2.3")
