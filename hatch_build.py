"""Build hook that makes jetstream's wheel platform-specific.

jetstream's wheel bundles pinned binary tools (and, for the website pack,
Node tools), so it is tagged ``py3-none-<platform>``: built once per release
per platform, then served from uv's cache whatever the Python version.

Downloading and verifying the binaries, and ``npm ci`` for the website pack,
come in later changes. Any failure stops the build with a one-line
``*** jetstream: ...`` message rather than a traceback.
"""

from __future__ import annotations

import platform
import sys
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

# (sys.platform, platform.machine()) -> wheel platform tag
SUPPORTED_PLATFORMS: dict[tuple[str, str], str] = {
    ("linux", "x86_64"): "linux_x86_64",
    ("linux", "aarch64"): "linux_aarch64",
    ("darwin", "arm64"): "macosx_11_0_arm64",
}


def fail(message: str) -> None:
    """Stop the build with a one-line message instead of a traceback."""
    sys.exit(f"*** jetstream: {message}")


def platform_tag(system: str | None = None, machine: str | None = None) -> str:
    """Return the wheel platform tag for this machine, or stop the build."""
    system = sys.platform if system is None else system
    machine = platform.machine() if machine is None else machine
    tag = SUPPORTED_PLATFORMS.get((system, machine))
    if tag is None:
        supported = ", ".join(f"{s} {m}" for s, m in SUPPORTED_PLATFORMS)
        fail(f"unsupported platform {system} {machine}; jetstream supports {supported}")
    return tag


class JetstreamBuildHook(BuildHookInterface):
    """Tag the wheel ``py3-none-<platform>``."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        """Set the wheel tag before hatchling builds the wheel."""
        if self.target_name != "wheel":
            return
        build_data["pure_python"] = False
        build_data["tag"] = f"py3-none-{platform_tag()}"
