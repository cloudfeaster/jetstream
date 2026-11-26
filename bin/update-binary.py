#!/usr/bin/env python3
"""Bump a binary tool's pin in binaries.toml, or check every pin is current.

    bin/update-binary.py TOOL VERSION   pin TOOL to VERSION
    bin/update-binary.py TOOL           pin TOOL to its latest release
    bin/update-binary.py --check        fail if any pin is behind its latest release, or GitHub reports a different license
    bin/update-binary.py --check -v     ... and report every tool's pinned and latest versions

A release is only used once it's at least 7 days old (the cooldown, as for
uv's exclude-newer and Dependabot), unless VERSION names it explicitly.
SHA-256s come from the digests GitHub records for each release asset, and
must match the checksums file the project publishes in the same release
(the pin's `checksums`), so a bump never rests on one source.

Set GITHUB_TOKEN to avoid the GitHub API's 60 requests/hour limit. An org
with an IP allow list (aquasecurity, for trivy) refuses any token from an IP
that isn't on its list, such as a GitHub runner's, even for a public repo
(https://github.com/aquasecurity/trivy/issues/10567). For such a tool,
--check reads the latest release from github.com's pages instead of the API,
and leaves its license to be checked when it's bumped, since a pinned
version's license can't change; a bump needs the API, so run it without
GITHUB_TOKEN there.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import tomlkit

if TYPE_CHECKING:
    from collections.abc import Mapping

PINS_PATH: Final[Path] = Path(__file__).resolve().parent.parent / "binaries.toml"
COOLDOWN: Final[dt.timedelta] = dt.timedelta(days=7)
API_TIMEOUT_SECONDS: Final[int] = 30


class UpdateError(Exception):
    """A problem to report in one line."""


class AllowListError(UpdateError):
    """The GitHub API refused GITHUB_TOKEN, because the repo's org has an IP allow list that this IP isn't on."""


def github_api(path: str) -> dict[str, Any]:
    """GET ``path`` from the GitHub REST API, with GITHUB_TOKEN if it's set."""
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    token: str | None = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        # The URL is written out here, so ruff's S310 can see it's https; bandit's B310 can't.
        with urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/{path}", headers=headers), timeout=API_TIMEOUT_SECONDS) as response:  # nosec B310
            return json.load(response)
    except urllib.error.HTTPError as e:
        error: str = f"GitHub API {path}: {e.code} {e.reason}{why(e)}"
        if token and e.code == HTTPStatus.FORBIDDEN and "IP allow list" in error:
            msg: str = f"{error}; run it without GITHUB_TOKEN"
            raise AllowListError(msg) from e
        raise UpdateError(error) from e
    except urllib.error.URLError as e:
        msg: str = f"GitHub API {path}: {e.reason}"
        raise UpdateError(msg) from e


def why(error: urllib.error.HTTPError) -> str:
    """Return GitHub's reason for refusing a request, and its rate-limit headers, to add to the error."""
    reason: str = ""
    try:
        message: object = json.loads(error.read()).get("message")
    except (ValueError, AttributeError):
        message = None
    if isinstance(message, str) and message:
        reason = f": {message}"
    limits: list[str] = []
    if (remaining := error.headers.get("x-ratelimit-remaining")) is not None:
        limits.append(f"{remaining} requests left")
    if (reset := error.headers.get("x-ratelimit-reset")) is not None and remaining == "0":
        limits.append(f"resets {dt.datetime.fromtimestamp(int(reset), dt.UTC):%Y-%m-%d %H:%M} UTC")
    if (retry_after := error.headers.get("retry-after")) is not None:
        limits.append(f"retry after {retry_after}s")
    if limits:
        reason += f" (rate limit: {', '.join(limits)})"
    return reason


def version_from_tag(tag_template: str, tag: str) -> str:
    """Return the version in ``tag``, given a template such as ``v{version}``."""
    prefix: str
    suffix: str
    prefix, _, suffix = tag_template.partition("{version}")
    if not (tag.startswith(prefix) and tag.endswith(suffix)):
        msg: str = f"release tag {tag} doesn't match {tag_template}"
        raise UpdateError(msg)
    return tag[len(prefix) : len(tag) - len(suffix)]


def released_at(release: dict[str, Any]) -> dt.datetime:
    """Return when ``release`` was published."""
    return dt.datetime.fromisoformat(release["published_at"])


def is_past_cooldown(release: dict[str, Any], now: dt.datetime) -> bool:
    """Return whether ``release`` is old enough to pin."""
    return now - released_at(release) >= COOLDOWN


def fetch(path: str) -> tuple[str, str]:
    """GET a page or release asset, by its URL after https://github.com/, following redirects; return the URL it ended at, and its text."""
    url: str = f"https://github.com/{path}"  # for messages
    try:
        # The URL is written out here, not taken from url, so ruff's S310 can see it's https; bandit's B310 can't.
        with urllib.request.urlopen(f"https://github.com/{path}", timeout=API_TIMEOUT_SECONDS) as response:  # nosec B310
            return response.geturl(), response.read().decode()
    except urllib.error.HTTPError as e:
        msg: str = f"{url}: {e.code} {e.reason}"
        raise UpdateError(msg) from e
    except urllib.error.URLError as e:
        msg: str = f"{url}: {e.reason}"
        raise UpdateError(msg) from e


def fetch_text(path: str) -> str:
    """GET a release asset, by its URL after https://github.com/, as text."""
    return fetch(path)[1]


def latest_release_from_web(repo: str) -> dict[str, Any]:
    """Return ``repo``'s latest release, its tag_name and published_at, from github.com's pages rather than its API.

    The tag is where /releases/latest redirects to. The date is the release's
    <updated> in /releases.atom, which lists the 10 newest releases: it's when
    the release was last changed, at or after it was published, so the
    cooldown is never shorter than the API's would be.
    """
    url: str = fetch(f"{repo}/releases/latest")[0]
    # under the repo's new name, if it's been renamed or moved
    page: re.Match[str] | None = re.fullmatch(r"https://github\.com/[^/]+/[^/]+/releases/tag/([^/?#]+)", url)
    if not page:
        msg: str = f"https://github.com/{repo}/releases/latest went to {url}, not a release"
        raise UpdateError(msg)
    tag: str = urllib.parse.unquote(page[1])
    for entry in re.findall(r"<entry>(.*?)</entry>", fetch_text(f"{repo}/releases.atom"), re.DOTALL):
        found: re.Match[str] | None = re.search(r"<id>tag:github\.com,2008:Repository/\d+/(.+?)</id>.*?<updated>(.+?)</updated>", entry, re.DOTALL)
        if found and found[1] == tag:
            return {"tag_name": tag, "published_at": found[2]}
    msg = f"https://github.com/{repo}/releases.atom has no release {tag}"
    raise UpdateError(msg)


def parse_checksums(text: str) -> dict[str, str]:
    """Parse ``sha256sum`` output (``<hex>  [*]<file>`` per line) into {file name: SHA-256}."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        match line.split(maxsplit=1):
            case [digest, path]:
                name: str = path.strip().lstrip("*").rsplit("/", 1)[-1]
                result[name] = digest.lower()
    return result


def platform_digests(pin: dict[str, Any], version: str, release: dict[str, Any]) -> dict[str, str]:
    """Return each platform's SHA-256 for ``version``, checked against the project's checksums."""
    assets: dict[str, dict[str, Any]] = {asset["name"]: asset for asset in release["assets"]}
    published: dict[str, dict[str, str]] = {}  # checksums file name -> its parsed contents
    result: dict[str, str] = {}
    for tag, platform_pin in pin["platforms"].items():
        asset: str = pin["asset"].format(version=version, platform=platform_pin["platform"])
        if asset not in assets:
            msg: str = f"release {release['tag_name']} has no asset {asset} (for {tag})"
            raise UpdateError(msg)
        digest: str | None = assets[asset].get("digest")
        if not digest or not digest.startswith("sha256:"):
            msg: str = f"GitHub has no SHA-256 digest for {asset} in release {release['tag_name']}"
            raise UpdateError(msg)
        sha256: str = digest.removeprefix("sha256:")

        checksums: str = pin["checksums"].format(version=version, asset=asset)
        if checksums not in published:
            if checksums not in assets:
                msg: str = f"release {release['tag_name']} has no checksums file {checksums}"
                raise UpdateError(msg)
            published[checksums] = parse_checksums(fetch_text(f"{pin['repo']}/releases/download/{release['tag_name']}/{checksums}"))
        if asset not in published[checksums]:
            msg: str = f"{checksums} in release {release['tag_name']} has no entry for {asset}"
            raise UpdateError(msg)
        if published[checksums][asset] != sha256:
            msg: str = f"{asset}: GitHub's digest {sha256} doesn't match {published[checksums][asset]} in {checksums}"
            raise UpdateError(
                msg,
            )
        result[tag] = sha256
    return result


def update(pins: tomlkit.TOMLDocument, tool: str, version: str | None, now: dt.datetime) -> str:
    """Pin ``tool`` to ``version`` (or its latest release) in ``pins``; return a summary line."""
    if tool not in pins:
        msg: str = f"no tool {tool} in {PINS_PATH.name}; tools are {', '.join(pins)}"
        raise UpdateError(msg)
    pin: Any = pins[tool]  # a tomlkit table, edited in place
    release: dict[str, Any]
    if version is None:
        release = github_api(f"repos/{pin['repo']}/releases/latest")
        version = version_from_tag(pin["tag"], release["tag_name"])
        if not is_past_cooldown(release, now):
            msg: str = f"{tool} {version} was released {released_at(release):%Y-%m-%d}, under {COOLDOWN.days} days ago; wait, or name the version to pin it anyway"
            raise UpdateError(
                msg,
            )
    else:
        tag: str = pin["tag"].format(version=version)
        release = github_api(f"repos/{pin['repo']}/releases/tags/{tag}")

    digests: dict[str, str] = platform_digests(pin, version, release)
    # The nightly --check can't compare the license of a tool whose org has an IP allow list, so a bump does.
    changed: str | None = license_change(tool, pin)
    if changed:
        raise UpdateError(changed)
    old_version: str = pin["version"]
    pin["version"] = version
    for tag, sha256 in digests.items():
        pin["platforms"][tag]["sha256"] = sha256
    if old_version == version:
        return f"{tool} {version}: already pinned; SHA-256s match GitHub's digests and the project's checksums"
    return f"{tool}: {old_version} -> {version}"


def license_change(tool: str, pin: Mapping[str, Any]) -> str | None:
    """Return a line if GitHub reports a different license for ``tool``'s repo than its pin records."""
    recorded: str = pin.get("github-license", pin["license"])
    reported: str = (github_api(f"repos/{pin['repo']}").get("license") or {}).get("spdx_id") or "none"
    if reported == recorded:
        return None
    return f"{tool}: GitHub reports the license {reported}, not {recorded}; review it, and update its license in {PINS_PATH.name}"


def latest_and_license(tool: str, pin: Mapping[str, Any]) -> tuple[dict[str, Any], str | None, str]:
    """Return ``tool``'s latest release, a line if its license changed, and a note to add to its report.

    If the API refuses GITHUB_TOKEN because of the org's IP allow list, the
    release comes from github.com's pages, and the license isn't compared.
    """
    try:
        return github_api(f"repos/{pin['repo']}/releases/latest"), license_change(tool, pin), ""
    except AllowListError:
        note: str = "; license not compared, as the org's IP allow list refuses the API here, so bumping it compares it"
        return latest_release_from_web(pin["repo"]), None, note


def check(pins: tomlkit.TOMLDocument, now: dt.datetime, *, verbose: bool = False) -> list[str]:
    """Return a line for each tool whose latest release past the cooldown isn't the pinned one, whose license changed, or that couldn't be checked.

    With ``verbose``, also print each tool's pinned and latest versions, and what that means.
    """
    stale: list[str] = []
    for tool, pin in pins.items():
        try:
            release: dict[str, Any]
            changed: str | None
            note: str
            release, changed, note = latest_and_license(tool, pin)
        except UpdateError as e:
            # Check the other tools anyway, so one failure doesn't hide what they'd report.
            stale.append(f"{tool}: couldn't check: {e}")
            if verbose:
                sys.stdout.write(stale[-1] + "\n")
            continue
        latest: str = version_from_tag(pin["tag"], release["tag_name"])
        status: str
        if latest == pin["version"]:
            status = "up to date"
        elif not is_past_cooldown(release, now):
            status = f"in the cooldown until {released_at(release) + COOLDOWN:%Y-%m-%d}, so {pin['version']} stays"
        else:
            status = "needs updating"
            stale.append(
                f"{tool} {pin['version']} is outdated: {latest} was released {released_at(release):%Y-%m-%d}; run bin/update-binary.py {tool}",
            )
        if changed:
            stale.append(changed)
        if verbose:
            sys.stdout.write(f"{tool}: pinned {pin['version']}; latest {latest} ({released_at(release):%Y-%m-%d}): {status}{note}\n")
    return stale


def main(argv: list[str] | None = None) -> int:
    """Run the command line."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if any pin is behind its latest release, or GitHub reports a different license")
    parser.add_argument("-v", "--verbose", action="store_true", help="with --check, report every tool, not just outdated ones")
    parser.add_argument("tool", nargs="?", help="the tool to update")
    parser.add_argument("version", nargs="?", help="the version to pin (default: the latest release)")
    args: argparse.Namespace = parser.parse_args(argv)
    if args.check == bool(args.tool):
        parser.error("give either --check or a TOOL")

    now: dt.datetime = dt.datetime.now(dt.UTC)
    pins: tomlkit.TOMLDocument = tomlkit.parse(PINS_PATH.read_text())
    try:
        if args.check:
            stale: list[str] = check(pins, now, verbose=args.verbose)
            for line in stale:
                sys.stderr.write(line + "\n")
            return 1 if stale else 0
        sys.stdout.write(update(pins, args.tool, args.version, now) + "\n")
    except UpdateError as e:
        sys.stderr.write(f"*** {e}\n")
        return 1
    updated: str = tomlkit.dumps(pins)
    # Only write a change: binaries.toml is a uv cache key, so writing it rebuilds jetstream.
    if updated != PINS_PATH.read_text():
        PINS_PATH.write_text(updated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
