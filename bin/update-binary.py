#!/usr/bin/env python3
"""Bump a binary tool's pin in binaries.toml, or check every pin is current.

    bin/update-binary.py TOOL VERSION   pin TOOL to VERSION
    bin/update-binary.py TOOL           pin TOOL to its latest release
    bin/update-binary.py --check        fail if any pin is behind its latest release
    bin/update-binary.py --check -v     ... and report every tool's pinned and latest versions

A release is only used once it's at least 7 days old (the cooldown, as for
uv's exclude-newer and Dependabot), unless VERSION names it explicitly.
SHA-256s come from the digests GitHub records for each release asset, and
must match the checksums file the project publishes in the same release
(the pin's `checksums`), so a bump never rests on one source.

Set GITHUB_TOKEN to avoid the GitHub API's 60 requests/hour limit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Final

import tomlkit

PINS_PATH: Final[Path] = Path(__file__).resolve().parent.parent / "binaries.toml"
COOLDOWN: Final[dt.timedelta] = dt.timedelta(days=7)
API_TIMEOUT_SECONDS: Final[int] = 30


class UpdateError(Exception):
    """A problem to report in one line."""


def github_api(path: str, *, authenticate: bool = True) -> Any:  # noqa: ANN401 (JSON)
    """GET ``path`` from the GitHub REST API, with GITHUB_TOKEN if it's set and ``authenticate``."""
    request: urllib.request.Request = urllib.request.Request(f"https://api.github.com/{path}")
    request.add_header("Accept", "application/vnd.github+json")
    token: str | None = os.environ.get("GITHUB_TOKEN") if authenticate else None
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:  # noqa: S310
            return json.load(response)
    except urllib.error.HTTPError as e:
        error: str = f"GitHub API {path}: {e.code} {e.reason}{why(e)}"
        # An org with an IP allow list (aquasecurity, for trivy) refuses a token from an IP
        # not on its list, such as a GitHub runner's, even for a public repo; it doesn't
        # refuse a request without one (https://github.com/aquasecurity/trivy/issues/10567).
        if token and e.code == 403 and "IP allow list" in error:  # noqa: PLR2004
            sys.stderr.write(f"*** {error}; retrying without GITHUB_TOKEN\n")
            return github_api(path, authenticate=False)
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


def fetch_text(url: str) -> str:
    """GET ``url`` (a release asset) as text."""
    try:
        with urllib.request.urlopen(url, timeout=API_TIMEOUT_SECONDS) as response:  # noqa: S310
            return response.read().decode()
    except urllib.error.HTTPError as e:
        msg: str = f"{url}: {e.code} {e.reason}"
        raise UpdateError(msg) from e
    except urllib.error.URLError as e:
        msg: str = f"{url}: {e.reason}"
        raise UpdateError(msg) from e


def parse_checksums(text: str) -> dict[str, str]:
    """Parse ``sha256sum`` output (``<hex>  [*]<file>`` per line) into {file name: SHA-256}."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        parts: list[str] = line.split(maxsplit=1)
        if len(parts) == 2:  # noqa: PLR2004 (hash and name)
            name: str = parts[1].strip().lstrip("*").rsplit("/", 1)[-1]
            result[name] = parts[0].lower()
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
            published[checksums] = parse_checksums(fetch_text(assets[checksums]["browser_download_url"]))
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
    old_version: str = pin["version"]
    pin["version"] = version
    for tag, sha256 in digests.items():
        pin["platforms"][tag]["sha256"] = sha256
    if old_version == version:
        return f"{tool} {version}: already pinned; SHA-256s match GitHub's digests and the project's checksums"
    return f"{tool}: {old_version} -> {version}"


def check(pins: tomlkit.TOMLDocument, now: dt.datetime, *, verbose: bool = False) -> list[str]:
    """Return a line for each tool whose latest release past the cooldown isn't the pinned one, or that couldn't be checked.

    With ``verbose``, also print each tool's pinned and latest versions, and what that means.
    """
    stale: list[str] = []
    for tool, pin in pins.items():
        try:
            release: dict[str, Any] = github_api(f"repos/{pin['repo']}/releases/latest")
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
        if verbose:
            sys.stdout.write(f"{tool}: pinned {pin['version']}; latest {latest} ({released_at(release):%Y-%m-%d}): {status}\n")
    return stale


def main(argv: list[str] | None = None) -> int:
    """Run the command line."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if any pin is behind its latest release")
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
