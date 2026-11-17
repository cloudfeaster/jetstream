#!/usr/bin/env python3
"""Bump a binary tool's pin in binaries.toml, or check every pin is current.

    bin/update-binary.py TOOL VERSION   pin TOOL to VERSION
    bin/update-binary.py TOOL           pin TOOL to its latest release
    bin/update-binary.py --check        fail if any pin is behind its latest release

A release is only used once it's at least 7 days old (the cooldown, as for
uv's exclude-newer and Dependabot), unless VERSION names it explicitly.
SHA-256s come from the digests GitHub records for each release asset.

Set GITHUB_TOKEN to avoid the GitHub API's 60 requests/hour limit.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Final

import tomlkit

PINS_PATH: Final[Path] = Path(__file__).resolve().parent.parent / "binaries.toml"
COOLDOWN: Final[datetime.timedelta] = datetime.timedelta(days=7)
API_TIMEOUT_SECONDS: Final[int] = 30


class UpdateError(Exception):
    """A problem to report in one line."""


def github_api(path: str) -> Any:  # noqa: ANN401 (JSON)
    """GET ``path`` from the GitHub REST API."""
    request: urllib.request.Request = urllib.request.Request(f"https://api.github.com/{path}")  # noqa: S310
    request.add_header("Accept", "application/vnd.github+json")
    if token := os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:  # noqa: S310
            return json.load(response)
    except urllib.error.HTTPError as e:
        raise UpdateError(f"GitHub API {path}: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise UpdateError(f"GitHub API {path}: {e.reason}") from e


def version_from_tag(tag_template: str, tag: str) -> str:
    """Return the version in ``tag``, given a template such as ``v{version}``."""
    prefix: str
    suffix: str
    prefix, _, suffix = tag_template.partition("{version}")
    if not (tag.startswith(prefix) and tag.endswith(suffix)):
        raise UpdateError(f"release tag {tag} doesn't match {tag_template}")
    return tag[len(prefix) : len(tag) - len(suffix)]


def released_at(release: dict[str, Any]) -> datetime.datetime:
    """Return when ``release`` was published."""
    return datetime.datetime.fromisoformat(release["published_at"])


def is_past_cooldown(release: dict[str, Any], now: datetime.datetime) -> bool:
    """Return whether ``release`` is old enough to pin."""
    return now - released_at(release) >= COOLDOWN


def platform_digests(pin: dict[str, Any], version: str, release: dict[str, Any]) -> dict[str, str]:
    """Return each platform's SHA-256 for ``version``, from ``release``'s asset digests."""
    digests: dict[str, str | None] = {asset["name"]: asset.get("digest") for asset in release["assets"]}
    result: dict[str, str] = {}
    for tag, platform_pin in pin["platforms"].items():
        asset: str = pin["asset"].format(version=version, platform=platform_pin["platform"])
        if asset not in digests:
            raise UpdateError(f"release {release['tag_name']} has no asset {asset} (for {tag})")
        digest: str | None = digests[asset]
        if not digest or not digest.startswith("sha256:"):
            raise UpdateError(f"GitHub has no SHA-256 digest for {asset} in release {release['tag_name']}")
        result[tag] = digest.removeprefix("sha256:")
    return result


def update(pins: tomlkit.TOMLDocument, tool: str, version: str | None, now: datetime.datetime) -> str:
    """Pin ``tool`` to ``version`` (or its latest release) in ``pins``; return a summary line."""
    if tool not in pins:
        raise UpdateError(f"no tool {tool} in {PINS_PATH.name}; tools are {', '.join(pins)}")
    pin: Any = pins[tool]  # a tomlkit table, edited in place
    release: dict[str, Any]
    if version is None:
        release = github_api(f"repos/{pin['repo']}/releases/latest")
        version = version_from_tag(pin["tag"], release["tag_name"])
        if not is_past_cooldown(release, now):
            raise UpdateError(
                f"{tool} {version} was released {released_at(release):%Y-%m-%d}, under {COOLDOWN.days} days ago; "
                f"wait, or name the version to pin it anyway",
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
        return f"{tool} {version}: already pinned; SHA-256s checked"
    return f"{tool}: {old_version} -> {version}"


def check(pins: tomlkit.TOMLDocument, now: datetime.datetime) -> list[str]:
    """Return a line for each tool whose latest release past the cooldown isn't the pinned one."""
    stale: list[str] = []
    for tool, pin in pins.items():
        release: dict[str, Any] = github_api(f"repos/{pin['repo']}/releases/latest")
        latest: str = version_from_tag(pin["tag"], release["tag_name"])
        if latest != pin["version"] and is_past_cooldown(release, now):
            stale.append(
                f"{tool} {pin['version']} is outdated: {latest} was released {released_at(release):%Y-%m-%d}; "
                f"run bin/update-binary.py {tool}",
            )
    return stale


def main(argv: list[str] | None = None) -> int:
    """Run the command line."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if any pin is behind its latest release")
    parser.add_argument("tool", nargs="?", help="the tool to update")
    parser.add_argument("version", nargs="?", help="the version to pin (default: the latest release)")
    args: argparse.Namespace = parser.parse_args(argv)
    if args.check == bool(args.tool):
        parser.error("give either --check or a TOOL")

    now: datetime.datetime = datetime.datetime.now(datetime.UTC)
    pins: tomlkit.TOMLDocument = tomlkit.parse(PINS_PATH.read_text())
    try:
        if args.check:
            stale: list[str] = check(pins, now)
            for line in stale:
                print(line, file=sys.stderr)
            return 1 if stale else 0
        print(update(pins, args.tool, args.version, now))
    except UpdateError as e:
        print(f"*** {e}", file=sys.stderr)
        return 1
    updated: str = tomlkit.dumps(pins)
    # Only write a change: binaries.toml is a uv cache key, so writing it rebuilds jetstream.
    if updated != PINS_PATH.read_text():
        PINS_PATH.write_text(updated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
