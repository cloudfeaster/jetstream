"""Build hook that bundles jetstream's binary tools into its wheel.

For this machine's platform, the hook downloads each binary tool pinned in
``binaries.toml``, checks its SHA-256 and adds it to the wheel's scripts, so
installing the wheel puts it in ``.venv/bin`` (decision 4). Each pack's
``run-*.sh`` scripts go there too (decision 8). The wheel is
tagged ``py3-none-<platform>``: built once per release per platform, then
served from uv's cache whatever the Python version.

Downloads are kept in ``$XDG_CACHE_HOME/jetstream/downloads`` (default
``~/.cache``), named by SHA-256, so rebuilding jetstream's own editable
install doesn't download them again. A cached file is checked again before
it's used.

Any failure stops the build with a one-line ``*** jetstream: ...`` message
rather than a traceback, and uv leaves the existing ``.venv`` as it was.
"""

from __future__ import annotations

import hashlib
import http.client
import os
import platform
import shutil
import sys
import tarfile
import tempfile
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import IO, Any, Final, NamedTuple, NoReturn, override

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

# (sys.platform, platform.machine()) -> wheel platform tag
SUPPORTED_PLATFORMS: Final[dict[tuple[str, str], str]] = {
    ("linux", "x86_64"): "linux_x86_64",
    ("linux", "aarch64"): "linux_aarch64",
    ("darwin", "arm64"): "macosx_11_0_arm64",
}

PINS_FILE: Final[str] = "binaries.toml"
SCRIPTS_GLOB: Final[str] = "src/jetstream/bin/*/*.sh"  # each pack's run-*.sh scripts
DOWNLOAD_TIMEOUT_SECONDS: Final[int] = 60
CHUNK_SIZE: Final[int] = 1024 * 1024


def fail(message: str) -> NoReturn:
    """Stop the build with a one-line message instead of a traceback."""
    sys.exit(f"*** jetstream: {message}")


def platform_tag(system: str | None = None, machine: str | None = None) -> str:
    """Return the wheel platform tag for this machine, or stop the build."""
    system: str = sys.platform if system is None else system
    machine: str = platform.machine() if machine is None else machine
    tag: str | None = SUPPORTED_PLATFORMS.get((system, machine))
    if tag is None:
        supported: str = ", ".join(f"{s} {m}" for s, m in SUPPORTED_PLATFORMS)
        fail(f"unsupported platform {system} {machine}; jetstream supports {supported}")
    return tag


class Binary(NamedTuple):
    """One pinned binary tool, resolved for one platform.

    A NamedTuple, not a dataclass: hatchling loads this file without adding
    it to sys.modules, which dataclasses need.
    """

    name: str
    version: str
    path: str  # the release asset's URL after https://github.com/
    member: str | None  # the executable inside a .tar.gz asset; None when the asset is the executable
    sha256: str

    @property
    def url(self) -> str:
        """Return the release asset's URL, for messages."""
        return f"https://github.com/{self.path}"


def load_binaries(pins_path: Path, tag: str) -> list[Binary]:
    """Read the pins in ``pins_path`` and resolve each tool for platform ``tag``."""
    try:
        pins: dict[str, Any] = tomllib.loads(pins_path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as e:
        fail(f"can't read {pins_path.name}: {e}")

    binaries: list[Binary] = []
    for name, pin in pins.items():
        try:
            version: str = pin["version"]
            platform_pin: dict[str, str] | None = pin["platforms"].get(tag)
            if platform_pin is None:
                fail(f"{pins_path.name} has no {tag} pin for {name}")
            fields: dict[str, str] = {"version": version, "platform": platform_pin["platform"]}
            tag_name: str = pin["tag"].format(**fields)
            asset: str = pin["asset"].format(**fields)
            binaries.append(
                Binary(
                    name=name,
                    version=version,
                    path=f"{pin['repo']}/releases/download/{tag_name}/{asset}",
                    member=pin["member"].format(**fields) if "member" in pin else None,
                    sha256=platform_pin["sha256"].lower(),
                ),
            )
        except (KeyError, TypeError, AttributeError) as e:
            fail(f"{pins_path.name}: bad pin for {name} ({e!r})")
    return binaries


def default_cache_dir() -> Path:
    """Return where downloads are cached, following the XDG base directory spec."""
    cache_home: str | Path = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(cache_home) / "jetstream" / "downloads"


def sha256_of(path: Path) -> str:
    """Return the hex SHA-256 of the file at ``path``."""
    digest: hashlib._Hash = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def download(binary: Binary, cache_dir: Path) -> Path:
    """Return the path of ``binary``'s release asset in ``cache_dir``, downloading it if needed.

    The file is only kept, and only returned, if its SHA-256 matches the pin.
    """
    cached: Path = cache_dir / binary.sha256
    if cached.is_file() and sha256_of(cached) == binary.sha256:
        return cached

    cache_dir.mkdir(parents=True, exist_ok=True)
    fd: int
    partial_name: str
    fd, partial_name = tempfile.mkstemp(dir=cache_dir, prefix=".partial-")
    partial: Path = Path(partial_name)
    try:
        digest: hashlib._Hash = hashlib.sha256()
        size: int = 0
        # The URL is written out here, not taken from binary.url, so ruff's S310
        # can see it's https: a download can never open a file: or other URL. bandit's B310 can't.
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(f"https://github.com/{binary.path}", timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:  # nosec B310
            while chunk := response.read(CHUNK_SIZE):
                digest.update(chunk)
                size += out.write(chunk)
            full_size: str | None = response.headers["Content-Length"]
        if full_size is not None and size < int(full_size):  # reading a response that's cut off raises no error
            fail(f"can't download {binary.name} {binary.version} from {binary.url}: it stopped after {size} of {full_size} bytes")
        if digest.hexdigest() != binary.sha256:
            fail(
                f"SHA-256 mismatch for {binary.name} {binary.version} from {binary.url}: expected {binary.sha256}, got {digest.hexdigest()}",
            )
        partial.replace(cached)
    except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
        reason: object = getattr(e, "reason", None) or e
        fail(f"can't download {binary.name} {binary.version} from {binary.url}: {reason}")
    finally:
        partial.unlink(missing_ok=True)
    return cached


def extract(binary: Binary, archive: Path, dest_dir: Path) -> Path:
    """Put ``binary``'s executable in ``dest_dir``: extracted from its ``.tar.gz`` ``archive``, or copied if it has no member."""
    dest: Path = dest_dir / binary.name
    if binary.member is None:
        shutil.copyfile(archive, dest)
        dest.chmod(0o755)
        return dest
    try:
        with tarfile.open(archive, "r:gz") as tar:
            member: tarfile.TarInfo = tar.getmember(binary.member)
            source: IO[bytes] | None = tar.extractfile(member) if member.isfile() else None
            if source is None:
                fail(f"{binary.member} in {binary.url} isn't a regular file")
            with source, dest.open("wb") as out:
                shutil.copyfileobj(source, out)
    except KeyError:
        fail(f"{binary.url} has no {binary.member}")
    except (tarfile.TarError, OSError) as e:
        fail(f"can't extract {binary.member} from {binary.url}: {e}")
    dest.chmod(0o755)
    return dest


def run_scripts(root: Path) -> list[Path]:
    """Return every pack's ``run-*.sh`` scripts, failing if two packs use the same name."""
    scripts: list[Path] = sorted(root.glob(SCRIPTS_GLOB))
    seen: dict[str, Path] = {}
    for script in scripts:
        if script.name in seen:
            fail(f"{script.relative_to(root)} and {seen[script.name].relative_to(root)} both install .venv/bin/{script.name}")
        seen[script.name] = script
    return scripts


class JetstreamBuildHook(BuildHookInterface):
    """Tag the wheel ``py3-none-<platform>`` and bundle the pinned binaries."""

    PLUGIN_NAME: str = "custom"  # overrides BuildHookInterface, so not Final

    @override
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Download, verify and extract the binaries before hatchling builds the wheel."""
        if self.target_name != "wheel":
            return
        tag: str = platform_tag()
        build_data["pure_python"] = False
        build_data["tag"] = f"py3-none-{tag}"

        self._work_dir: Path = Path(tempfile.mkdtemp(prefix="jetstream-build-"))
        try:
            cache_dir: Path = default_cache_dir()
            for binary in load_binaries(Path(self.root) / PINS_FILE, tag):
                executable: Path = extract(binary, download(binary, cache_dir), self._work_dir)
                build_data["shared_scripts"][str(executable)] = binary.name
            for script in run_scripts(Path(self.root)):
                build_data["shared_scripts"][str(script)] = script.name
        except BaseException:  # hatchling doesn't call finalize() after a failure, and fail() raises SystemExit
            shutil.rmtree(self._work_dir, ignore_errors=True)
            raise

    @override
    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        """Remove the extracted binaries once the wheel is written."""
        work_dir: Path | None = getattr(self, "_work_dir", None)
        if work_dir is not None:
            shutil.rmtree(work_dir, ignore_errors=True)
