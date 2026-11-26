"""Tests for jetstream.dist_check, the website pack's check of what a site publishes."""

import struct
import zlib
from pathlib import Path

import pytest

from jetstream import dist_check


def png(*chunks: bytes) -> bytes:
    """Return a PNG with an IHDR, then a chunk of each type in ``chunks``, then IEND."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    body: bytes = b"".join(chunk(kind, b"Author\x00someone") for kind in chunks)
    return dist_check.PNG_SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)) + body + chunk(b"IEND", b"")


def jpeg(*segments: bytes) -> bytes:
    """Return a JPEG's start, an APP0 (JFIF), an APP1 with each payload in ``segments``, then the start of its scan."""

    def segment(marker: int, payload: bytes) -> bytes:
        return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload

    return b"\xff\xd8" + segment(0xE0, b"JFIF\x00\x01\x01") + b"".join(segment(0xE1, payload) for payload in segments) + b"\xff\xda\x00\x02" + b"Exif\x00\x00 in the image data"


def webp(*chunks: bytes) -> bytes:
    """Return a WebP with a VP8X chunk, a chunk of each type in ``chunks`` (odd-sized, so padded), then an image."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return kind + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) % 2 else b"")

    body: bytes = chunk(b"VP8X", b"\x00" * 10) + b"".join(chunk(kind, b"odd") for kind in chunks) + chunk(b"VP8L", b"image")
    return b"RIFF" + struct.pack("<I", len(body) + 4) + b"WEBP" + body


@pytest.mark.parametrize(
    ("data", "metadata"),
    [
        (png(), []),
        (png(b"pHYs", b"iCCP"), []),
        (png(b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"tIME"), ["tEXt", "iTXt", "zTXt", "eXIf", "tIME"]),
        (png(b"tEXt")[:-20], ["tEXt"]),
        (jpeg(), []),
        (jpeg(b"Exif\x00\x00II*\x00"), ["EXIF"]),
        (jpeg(b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta/>"), ["XMP"]),
        (jpeg(b"Exif\x00\x00MM", b"http://ns.adobe.com/xap/1.0/\x00<x/>"), ["EXIF", "XMP"]),
        (jpeg(b"ICC_PROFILE\x00"), []),
        (jpeg()[:5], []),
        (webp(), []),
        (webp(b"ICCP"), []),
        (webp(b"EXIF", b"XMP "), ["EXIF", "XMP"]),
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", []),
        (b"", []),
    ],
    ids=[
        "png",
        "png-color-only",
        "png-metadata",
        "png-truncated",
        "jpeg",
        "jpeg-exif",
        "jpeg-xmp",
        "jpeg-both",
        "jpeg-color-profile",
        "jpeg-truncated",
        "webp",
        "webp-color-profile",
        "webp-metadata",
        "not-an-image",
        "empty",
    ],
)
def test_image_metadata_finds_what_identifies_an_image(data: bytes, metadata: list[str]) -> None:
    """Text, EXIF, XMP and time chunks are found; color information, an image's own data, and what isn't an image aren't; a truncated image is read as far as it goes."""
    assert dist_check.image_metadata(data) == metadata


def write(dist: Path, files: dict[str, bytes]) -> None:
    """Write ``files`` into ``dist``, by path."""
    for name, content in files.items():
        path: Path = dist / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def test_a_clean_site_passes(tmp_path: Path) -> None:
    """Pages, styles, scripts, fonts, images without metadata and .well-known/ are what a site publishes."""
    dist: Path = tmp_path / "dist"
    write(dist, {"index.html": b"<html></html>", "about/index.html": b"", "_astro/a.css": b"", "_astro/a.js": b"", "logo.png": png(), "photo.jpg": jpeg(), "photo.webp": webp(), ".well-known/security.txt": b"Contact: x"})
    assert dist_check.problems(dist) == []


def test_what_a_site_shouldnt_publish_fails(tmp_path: Path) -> None:
    """A source map, a hidden file or folder (named once, not each file in it), and an image with metadata each fail, by path."""
    dist: Path = tmp_path / "dist"
    write(
        dist,
        {
            "index.html": b"",
            "_astro/a.js.map": b"{}",
            ".env": b"KEY=1",
            "img/.DS_Store": b"",
            ".git/config": b"",
            ".git/HEAD": b"",
            "about/.well-known/x": b"",
            "logo.png": png(b"tEXt"),
            "photo.jpg": jpeg(b"Exif\x00\x00II"),
        },
    )
    assert dist_check.problems(dist) == [
        "dist/.env: a hidden file",
        "dist/.git: a hidden folder",
        "dist/_astro/a.js.map: a source map",
        "dist/about/.well-known: a hidden folder",
        "dist/img/.DS_Store: a hidden file",
        "dist/logo.png: metadata in the image (tEXt)",
        "dist/photo.jpg: metadata in the image (EXIF)",
    ]


def test_main_prints_each_problem(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """main() prints each problem and returns 1, or prints nothing and returns 0."""
    dist: Path = tmp_path / "dist"
    write(dist, {"index.html": b""})
    assert dist_check.main([str(dist)]) == 0
    write(dist, {"a.js.map": b""})
    assert dist_check.main([str(dist)]) == 1
    assert capsys.readouterr().out == "dist/a.js.map: a source map\n"
