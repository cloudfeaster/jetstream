"""Tests for the wheel-tagging build hook in hatch_build.py."""

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("hatch_build", Path(__file__).parent.parent / "hatch_build.py")
assert _spec is not None
assert _spec.loader is not None
hatch_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hatch_build)


@pytest.mark.parametrize(
    ("system", "machine", "tag"),
    [
        ("linux", "x86_64", "linux_x86_64"),
        ("linux", "aarch64", "linux_aarch64"),
        ("darwin", "arm64", "macosx_11_0_arm64"),
    ],
)
def test_supported_platforms(system: str, machine: str, tag: str) -> None:
    assert hatch_build.platform_tag(system, machine) == tag


@pytest.mark.parametrize(
    ("system", "machine"),
    [
        ("darwin", "x86_64"),
        ("win32", "AMD64"),
        ("linux", "armv7l"),
    ],
)
def test_unsupported_platform_stops_build_with_one_line_message(system: str, machine: str) -> None:
    with pytest.raises(SystemExit) as exc_info:
        hatch_build.platform_tag(system, machine)
    message = str(exc_info.value.code)
    assert message.startswith(f"*** jetstream: unsupported platform {system} {machine};")
    assert "\n" not in message


def test_this_machine_is_supported() -> None:
    # jetstream's own CI and dev machines must be able to build jetstream.
    assert hatch_build.platform_tag() in hatch_build.SUPPORTED_PLATFORMS.values()
