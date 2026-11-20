"""Tests for jetstream.update, the file-handling half of run-update-jetstream.sh."""

import io
import json
import re
from pathlib import Path
from typing import Any, Final

import pytest

from jetstream import update

PINNED: Final[str] = """\
[dependency-groups]
dev = ["cloudfeaster-jetstream[core]"]

[tool.uv.sources]
# Pinned to a release tag.
cloudfeaster-jetstream = { git = "https://github.com/cloudfeaster/jetstream", tag = "v0.4.0" }  # bumped by jetstream-update.yaml
"""

LS_REMOTE: Final[str] = "".join(f"{n:040x}\trefs/tags/{tag}\n" for n, tag in enumerate(("v0.4.0", "v0.10.0", "v0.9.1", "probe-bad", "v1.0.0-rc1")))


@pytest.mark.parametrize(
    "pyproject",
    [
        "[project]\nname = 'x'\n",  # no sources
        "[tool.uv.sources]\ncloudfeaster-jetstream = { workspace = true }\n",  # jetstream itself
        "[tool.uv.sources]\ncloudfeaster-jetstream = { git = 'https://example.com/j', branch = 'main' }\n",
        "[tool.uv.sources]\ncloudfeaster-jetstream = { git = 'https://example.com/j', tag = 'nightly' }\n",
    ],
)
def test_no_pin_unless_jetstream_is_pinned_to_a_release_tag(pyproject: str) -> None:
    """Only a git source with a vX.Y.Z tag is a pin the update can bump."""
    assert update.pin(pyproject) is None


def test_pin_is_the_git_url_and_tag() -> None:
    """A release pin gives the repo to look for tags in, and the current tag."""
    assert update.pin(PINNED) == ("https://github.com/cloudfeaster/jetstream", "v0.4.0")


def test_newer_is_the_latest_release_by_version_not_by_name() -> None:
    """v0.10.0 is newer than v0.9.1, and tags that aren't vX.Y.Z are ignored."""
    assert update.newer("v0.4.0", LS_REMOTE) == "v0.10.0"


@pytest.mark.parametrize("current", ["v0.10.0", "v0.11.0"])
def test_nothing_is_newer_than_the_latest_release(current: str) -> None:
    """With the latest release pinned, or a newer one, there's nothing to take."""
    assert update.newer(current, LS_REMOTE) is None


def test_set_pin_changes_only_the_tag() -> None:
    """The tag changes; the comments and the rest of the file don't."""
    assert update.set_pin(PINNED, "v0.10.0") == PINNED.replace('tag = "v0.4.0"', 'tag = "v0.10.0"')


def test_set_pin_needs_a_jetstream_source() -> None:
    """A pyproject.toml without jetstream's source is an error."""
    with pytest.raises(update.UpdateError, match=re.escape("no [tool.uv.sources] cloudfeaster-jetstream")):
        update.set_pin("[project]\nname = 'x'\n", "v0.10.0")


def test_tree_lists_each_change(tmp_path: Path) -> None:
    """A changed or new file is sent with its content and mode, and a deleted one with no SHA."""
    (tmp_path / "uv.lock").write_text("lock\n")
    (tmp_path / "cfg4dev.sh").write_text("#!/bin/bash\n")
    (tmp_path / "cfg4dev.sh").chmod(0o755)
    status: bytes = b" M uv.lock\0?? cfg4dev.sh\0 D .github/workflows/jetstream-old.yaml\0"
    request: dict[str, Any] = update.tree(tmp_path, status, "base")
    assert request == {
        "base_tree": "base",
        "tree": [
            {"path": "uv.lock", "mode": "100644", "type": "blob", "content": "lock\n"},
            {"path": "cfg4dev.sh", "mode": "100755", "type": "blob", "content": "#!/bin/bash\n"},
            {"path": ".github/workflows/jetstream-old.yaml", "mode": "100644", "type": "blob", "sha": None},
        ],
    }


def test_tree_rejects_a_file_that_isnt_text(tmp_path: Path) -> None:
    """The trees API takes content as text, so a binary file is an error."""
    (tmp_path / "image.png").write_bytes(b"\x89PNG\xff")
    with pytest.raises(update.UpdateError, match=re.escape("image.png: not UTF-8 text")):
        update.tree(tmp_path, b"?? image.png\0", "base")


def test_main_runs_each_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """pin, newer, set-pin and tree read and write what the script expects."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(PINNED)
    assert update.main(["pin"]) == update.EXIT_OK
    assert capsys.readouterr().out == "https://github.com/cloudfeaster/jetstream\tv0.4.0\n"

    monkeypatch.setattr("sys.stdin", io.StringIO(LS_REMOTE))
    assert update.main(["newer", "v0.4.0"]) == update.EXIT_OK
    assert capsys.readouterr().out == "v0.10.0\n"

    assert update.main(["set-pin", "v0.10.0"]) == update.EXIT_OK
    assert update.pin((tmp_path / "pyproject.toml").read_text()) == ("https://github.com/cloudfeaster/jetstream", "v0.10.0")

    (tmp_path / "status").write_bytes(b" M pyproject.toml\0")
    assert update.main(["tree", "status", "base"]) == update.EXIT_OK
    sent: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert [entry["path"] for entry in sent["tree"]] == ["pyproject.toml"]


@pytest.mark.parametrize("argv", [[], ["newer", "latest"], ["set-pin", "main"], ["tree", "status"]])
def test_main_reports_a_bad_command(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    """A missing command, or a tag that isn't vX.Y.Z, prints the usage."""
    assert update.main(argv) == update.EXIT_ERROR
    assert capsys.readouterr().err == update.USAGE


def test_main_reports_an_update_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """An UpdateError is one line on stderr."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    assert update.main(["set-pin", "v0.10.0"]) == update.EXIT_ERROR
    assert capsys.readouterr().err.startswith("*** jetstream update: pyproject.toml has no")
