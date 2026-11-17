"""Until `jetstream sync` exists, jetstream keeps hand-made copies of its core owned files."""

from pathlib import Path
from typing import Final

import pytest

ROOT: Final[Path] = Path(__file__).parent.parent
CORE_FILES: Final[Path] = ROOT / "src" / "jetstream" / "files" / "core"


@pytest.mark.parametrize("owned", sorted(CORE_FILES.iterdir()), ids=lambda path: path.name)
def test_jetstream_uses_its_own_core_files(owned: Path) -> None:
    copy: Path = ROOT / owned.name
    assert copy.read_text() == owned.read_text(), f"cp {owned.relative_to(ROOT)} {owned.name}"
