"""Tests for the build hook in hatch_build.py."""

import hashlib
import importlib.machinery
import importlib.util
import io
import sys
import tarfile
import tomllib
import types
from pathlib import Path
from typing import Any, Final

import pytest

ROOT: Final[Path] = Path(__file__).parent.parent
BINARIES: Final[set[str]] = {"mado", "d2", "gitleaks", "trivy", "jq"}
SHA256_HEX_LENGTH: Final[int] = 64
EXECUTABLE_MODE: Final[int] = 0o755

_spec: importlib.machinery.ModuleSpec | None = importlib.util.spec_from_file_location("hatch_build", ROOT / "hatch_build.py")
assert _spec is not None
assert _spec.loader is not None
hatch_build: types.ModuleType = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hatch_build)


def assert_one_line_failure(exc_info: pytest.ExceptionInfo[SystemExit], start: str) -> None:
    """Assert the build stopped with one ``*** jetstream:`` line starting with ``start``."""
    message: str = str(exc_info.value.code)
    assert message.startswith(f"*** jetstream: {start}"), message
    assert "\n" not in message


@pytest.mark.parametrize(
    ("system", "machine", "tag"),
    [
        ("linux", "x86_64", "linux_x86_64"),
        ("linux", "aarch64", "linux_aarch64"),
        ("darwin", "arm64", "macosx_11_0_arm64"),
    ],
)
def test_supported_platforms(system: str, machine: str, tag: str) -> None:
    """Each supported OS and machine maps to its wheel platform tag."""
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
    """Intel macOS, Windows and 32-bit ARM stop the build, naming the platform."""
    with pytest.raises(SystemExit) as exc_info:
        hatch_build.platform_tag(system, machine)
    assert_one_line_failure(exc_info, f"unsupported platform {system} {machine};")


def test_this_machine_is_supported() -> None:
    """The machine running the tests can build jetstream."""
    # jetstream's own CI and dev machines must be able to build jetstream.
    assert hatch_build.platform_tag() in hatch_build.SUPPORTED_PLATFORMS.values()


# --- binaries.toml


def test_every_tool_is_pinned_for_every_supported_platform() -> None:
    """binaries.toml pins each tool for every supported platform, with its project's checksums file."""
    pins: dict[str, Any] = tomllib.loads((ROOT / hatch_build.PINS_FILE).read_text())
    for name, pin in pins.items():
        assert set(pin["platforms"]) == set(hatch_build.SUPPORTED_PLATFORMS.values()), name
        assert "checksums" in pin, f"{name} needs the project's checksums file, for bin/update-binary.py"


def test_every_pin_resolves() -> None:
    """Every pin in binaries.toml resolves to a GitHub release URL and a full SHA-256, on every platform."""
    for tag in hatch_build.SUPPORTED_PLATFORMS.values():
        binaries: list[hatch_build.Binary] = hatch_build.load_binaries(ROOT / hatch_build.PINS_FILE, tag)
        assert {b.name for b in binaries} == BINARIES
        for binary in binaries:
            assert binary.url.startswith("https://github.com/")
            assert len(binary.sha256) == SHA256_HEX_LENGTH


def test_load_binaries_fills_in_version_and_platform(tmp_path: Path) -> None:
    """The version and platform fill in the tag, asset and member templates, and the SHA-256 is lower-cased."""
    pins: Path = tmp_path / "binaries.toml"
    pins.write_text(
        """
[tool]
repo = "owner/tool"
version = "1.2.3"
tag = "v{version}"
asset = "tool-{version}-{platform}.tar.gz"
member = "tool-v{version}/bin/tool"

[tool.platforms]
linux_x86_64 = { platform = "linux-amd64", sha256 = "ABC" }
""",
    )
    [binary] = hatch_build.load_binaries(pins, "linux_x86_64")
    assert binary == hatch_build.Binary(
        name="tool",
        version="1.2.3",
        url="https://github.com/owner/tool/releases/download/v1.2.3/tool-1.2.3-linux-amd64.tar.gz",
        member="tool-v1.2.3/bin/tool",
        sha256="abc",
    )


def test_load_binaries_fails_on_missing_platform(tmp_path: Path) -> None:
    """A tool with no pin for the build's platform stops the build."""
    pins: Path = tmp_path / "binaries.toml"
    pins.write_text(
        """
[tool]
repo = "owner/tool"
version = "1.2.3"
tag = "v{version}"
asset = "tool.tar.gz"
member = "tool"
platforms = {}
""",
    )
    with pytest.raises(SystemExit) as exc_info:
        hatch_build.load_binaries(pins, "linux_x86_64")
    assert_one_line_failure(exc_info, "binaries.toml has no linux_x86_64 pin for tool")


def test_load_binaries_fails_on_bad_pin(tmp_path: Path) -> None:
    """A pin missing required keys stops the build, naming the tool."""
    pins: Path = tmp_path / "binaries.toml"
    pins.write_text('[tool]\nversion = "1"\n')
    with pytest.raises(SystemExit) as exc_info:
        hatch_build.load_binaries(pins, "linux_x86_64")
    assert_one_line_failure(exc_info, "binaries.toml: bad pin for tool")


# --- download and extract


def make_archive(path: Path, members: dict[str, bytes]) -> str:
    """Write a .tar.gz of ``members`` to ``path`` and return its SHA-256."""
    with tarfile.open(path, "w:gz") as tar:
        for name, content in members.items():
            info: tarfile.TarInfo = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binary_for(archive: Path, sha256: str, member: str = "dir/tool") -> "hatch_build.Binary":
    """Return a Binary that downloads ``archive`` from a file URL."""
    return hatch_build.Binary(name="tool", version="1.2.3", url=archive.as_uri(), member=member, sha256=sha256)


def test_download_verifies_and_caches(tmp_path: Path) -> None:
    """A verified download is cached by its SHA-256, and a later build uses the cache."""
    archive: Path = tmp_path / "tool.tar.gz"
    sha256: str = make_archive(archive, {"dir/tool": b"#!/bin/sh\necho tool\n"})
    cache_dir: Path = tmp_path / "cache"

    cached: Path = hatch_build.download(binary_for(archive, sha256), cache_dir)
    assert cached == cache_dir / sha256
    assert cached.read_bytes() == archive.read_bytes()

    # A second build uses the cache, so the source can be gone.
    archive.unlink()
    assert hatch_build.download(binary_for(archive, sha256), cache_dir) == cached


def test_download_replaces_a_corrupt_cached_file(tmp_path: Path) -> None:
    """A cached file that fails verification is downloaded again."""
    archive: Path = tmp_path / "tool.tar.gz"
    sha256: str = make_archive(archive, {"dir/tool": b"tool"})
    cache_dir: Path = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / sha256).write_bytes(b"corrupt")

    cached: Path = hatch_build.download(binary_for(archive, sha256), cache_dir)
    assert cached.read_bytes() == archive.read_bytes()


def test_download_fails_on_sha256_mismatch_and_keeps_nothing(tmp_path: Path) -> None:
    """A download with the wrong SHA-256 stops the build and leaves nothing in the cache."""
    archive: Path = tmp_path / "tool.tar.gz"
    make_archive(archive, {"dir/tool": b"tool"})
    cache_dir: Path = tmp_path / "cache"

    with pytest.raises(SystemExit) as exc_info:
        hatch_build.download(binary_for(archive, "0" * 64), cache_dir)
    assert_one_line_failure(exc_info, "SHA-256 mismatch for tool 1.2.3 from file://")
    assert list(cache_dir.iterdir()) == []


def test_download_fails_cleanly_when_the_download_fails(tmp_path: Path) -> None:
    """A download that can't be fetched stops the build and leaves nothing in the cache."""
    cache_dir: Path = tmp_path / "cache"
    with pytest.raises(SystemExit) as exc_info:
        hatch_build.download(binary_for(tmp_path / "missing.tar.gz", "0" * 64), cache_dir)
    assert_one_line_failure(exc_info, "can't download tool 1.2.3 from file://")
    assert list(cache_dir.iterdir()) == []


def test_extract_writes_an_executable(tmp_path: Path) -> None:
    """Only the named member is extracted, as an executable named after the tool."""
    archive: Path = tmp_path / "tool.tar.gz"
    sha256: str = make_archive(archive, {"dir/README": b"readme", "dir/tool": b"tool"})
    dest_dir: Path = tmp_path / "out"
    dest_dir.mkdir()

    executable: Path = hatch_build.extract(binary_for(archive, sha256), archive, dest_dir)
    assert executable == dest_dir / "tool"
    assert executable.read_bytes() == b"tool"
    assert executable.stat().st_mode & 0o777 == EXECUTABLE_MODE


def test_extract_copies_an_asset_that_is_the_executable(tmp_path: Path) -> None:
    """An asset with no member is the executable itself, so it's copied."""
    asset: Path = tmp_path / "tool-linux-amd64"
    asset.write_bytes(b"tool")
    dest_dir: Path = tmp_path / "out"
    dest_dir.mkdir()
    binary: hatch_build.Binary = binary_for(asset, "0" * 64)._replace(member=None)

    executable: Path = hatch_build.extract(binary, asset, dest_dir)
    assert executable == dest_dir / "tool"
    assert executable.read_bytes() == b"tool"
    assert executable.stat().st_mode & 0o777 == EXECUTABLE_MODE


def test_load_binaries_without_a_member(tmp_path: Path) -> None:
    """A pin with no member is for an asset that's the executable itself."""
    pins: Path = tmp_path / "binaries.toml"
    pins.write_text(
        """
[tool]
repo = "owner/tool"
version = "1.2.3"
tag = "tool-{version}"
asset = "tool-{platform}"

[tool.platforms]
linux_x86_64 = { platform = "linux-amd64", sha256 = "abc" }
""",
    )
    [binary] = hatch_build.load_binaries(pins, "linux_x86_64")
    assert binary.member is None
    assert binary.url == "https://github.com/owner/tool/releases/download/tool-1.2.3/tool-linux-amd64"


def test_extract_fails_on_missing_member(tmp_path: Path) -> None:
    """An archive without the pinned member stops the build."""
    archive: Path = tmp_path / "tool.tar.gz"
    sha256: str = make_archive(archive, {"other": b"x"})
    with pytest.raises(SystemExit) as exc_info:
        hatch_build.extract(binary_for(archive, sha256), archive, tmp_path)
    assert_one_line_failure(exc_info, f"{archive.as_uri()} has no dir/tool")


def test_extract_fails_on_a_corrupt_archive(tmp_path: Path) -> None:
    """A file that isn't a valid archive stops the build."""
    archive: Path = tmp_path / "tool.tar.gz"
    archive.write_bytes(b"not a tarball")
    with pytest.raises(SystemExit) as exc_info:
        hatch_build.extract(binary_for(archive, "0" * 64), archive, tmp_path)
    assert_one_line_failure(exc_info, "can't extract dir/tool from file://")


# --- run-*.sh scripts


def test_run_scripts_are_found() -> None:
    """Every pack's run-*.sh scripts are found, and nothing else."""
    names: list[str] = [script.name for script in hatch_build.run_scripts(ROOT)]
    assert "run-mado.sh" in names
    assert all(name.startswith("run-") and name.endswith(".sh") for name in names)


def test_run_scripts_fails_on_a_name_used_by_two_packs(tmp_path: Path) -> None:
    """Two packs can't both install a script with the same name into .venv/bin."""
    for pack in ("core", "python"):
        (tmp_path / "src" / "jetstream" / "bin" / pack).mkdir(parents=True)
        (tmp_path / "src" / "jetstream" / "bin" / pack / "run-x.sh").write_text("")
    with pytest.raises(SystemExit) as exc_info:
        hatch_build.run_scripts(tmp_path)
    assert_one_line_failure(exc_info, "src/jetstream/bin/python/run-x.sh and src/jetstream/bin/core/run-x.sh both install")


# --- jetstream's own .venv


@pytest.mark.parametrize("name", sorted(BINARIES))
def test_binaries_are_installed_in_this_venv(name: str) -> None:
    """Each pinned binary is an executable in jetstream's own .venv/bin."""
    # uv installs jetstream into its own .venv, so the build hook has run.
    executable: Path = Path(sys.prefix) / "bin" / name
    assert executable.is_file()
    assert executable.stat().st_mode & 0o111


@pytest.mark.parametrize("script", hatch_build.run_scripts(ROOT), ids=lambda script: script.name)
def test_run_scripts_are_installed_in_this_venv(script: Path) -> None:
    """Each run-*.sh in .venv/bin is executable and matches its source, so uv rebuilt jetstream after a change."""
    installed: Path = Path(sys.prefix) / "bin" / script.name
    assert installed.read_bytes() == script.read_bytes(), "rebuild with uv sync"
    assert installed.stat().st_mode & 0o111
