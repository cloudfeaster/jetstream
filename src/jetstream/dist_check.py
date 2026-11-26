"""The website pack's check of what a site publishes, run by its ``run-check-dist.sh``.

Everything in ``dist/``, from ``astro build``, is deployed as it is, so this
fails on what a site shouldn't publish by mistake, besides secrets, which
gitleaks looks for:

- a source map (``*.map``), which gives away the site's source;
- a hidden file or folder, such as ``.env`` or ``.DS_Store``, except
  ``.well-known/`` at the top, which is meant to be published;
- metadata in an image, such as its camera, GPS location, author or the
  software that made it: text and EXIF chunks and the time in a PNG
  (``tEXt``, ``iTXt``, ``zTXt``, ``eXIf``, ``tIME``), and EXIF and XMP in a
  JPEG or WebP. Astro strips it from the images it processes, but copies
  ``public/`` as it is.

An image this can't read is left alone: it's the browser's problem, not a leak.

Usage, printing each problem (exit 1)::

    python -m jetstream.dist_check DIST
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Final

PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
PNG_METADATA: Final[frozenset[bytes]] = frozenset({b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"tIME"})
JPEG_METADATA: Final[dict[bytes, str]] = {b"Exif\x00\x00": "EXIF", b"http://ns.adobe.com/xap/1.0/\x00": "XMP"}
WEBP_METADATA: Final[dict[bytes, str]] = {b"EXIF": "EXIF", b"XMP ": "XMP"}
JPEG_APP1: Final[int] = 0xE1
JPEG_START_OF_SCAN: Final[int] = 0xDA  # the image data, after every metadata segment


def png_metadata(data: bytes) -> list[str]:
    """Return the names of the metadata chunks in PNG ``data``, in order."""
    found: list[str] = []
    position: int = len(PNG_SIGNATURE)
    while position + 8 <= len(data):
        length: int
        kind: bytes
        length, kind = struct.unpack(">I4s", data[position : position + 8])
        if kind in PNG_METADATA:
            found.append(kind.decode())
        position += 12 + length  # length, type, data, CRC
    return found


def jpeg_metadata(data: bytes) -> list[str]:
    """Return the kinds of metadata (EXIF, XMP) in JPEG ``data``, in order."""
    found: list[str] = []
    position: int = 2  # after the start-of-image marker
    while position + 4 <= len(data) and data[position] == 0xFF:  # noqa: PLR2004 (a JPEG marker's first byte)
        marker: int = data[position + 1]
        if marker == JPEG_START_OF_SCAN:
            break
        length: int = struct.unpack(">H", data[position + 2 : position + 4])[0]
        if marker == JPEG_APP1:
            segment: bytes = data[position + 4 : position + 2 + length]
            found.extend(kind for prefix, kind in JPEG_METADATA.items() if segment.startswith(prefix))
        position += 2 + length
    return found


def webp_metadata(data: bytes) -> list[str]:
    """Return the kinds of metadata (EXIF, XMP) in WebP ``data``, in order."""
    found: list[str] = []
    position: int = 12  # after RIFF, the size and WEBP
    while position + 8 <= len(data):
        kind: bytes
        length: int
        kind, length = struct.unpack("<4sI", data[position : position + 8])
        if kind in WEBP_METADATA:
            found.append(WEBP_METADATA[kind])
        position += 8 + length + (length % 2)  # a chunk is padded to an even size
    return found


def image_metadata(data: bytes) -> list[str]:
    """Return the metadata in image ``data``, a PNG, JPEG or WebP; anything else has none this can find."""
    if data.startswith(PNG_SIGNATURE):
        return png_metadata(data)
    if data.startswith(b"\xff\xd8"):
        return jpeg_metadata(data)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return webp_metadata(data)
    return []


def problems(dist: Path) -> list[str]:
    """Return a line for each thing under ``dist`` that a site shouldn't publish, by path."""
    found: list[str] = []
    for path in sorted(dist.rglob("*")):
        relative: Path = path.relative_to(dist)
        hidden: list[str] = [part for part in relative.parts if part.startswith(".")]
        if hidden and relative.parts[0] != ".well-known":
            if relative.name.startswith("."):  # each hidden name once, not every file under a hidden folder
                found.append(f"{dist.name}/{relative}: a hidden {'folder' if path.is_dir() else 'file'}")
            continue
        if not path.is_file():
            continue
        if path.suffix == ".map":
            found.append(f"{dist.name}/{relative}: a source map")
            continue
        metadata: list[str] = image_metadata(path.read_bytes())
        if metadata:
            found.append(f"{dist.name}/{relative}: metadata in the image ({', '.join(metadata)})")
    return found


def main(argv: list[str]) -> int:
    """Check the folder named in ``argv``, printing each problem; return 1 if there are any."""
    found: list[str] = problems(Path(argv[0]))
    for line in found:
        sys.stdout.write(f"{line}\n")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
