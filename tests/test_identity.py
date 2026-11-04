"""Identity build: a fresh unpack + repack with no edits gives the original disc, byte for byte."""
import filecmp
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402

ORIG = ROOT / "rom/Bealphareth (Japan).bin"


@pytest.mark.skipif(not ORIG.exists() or not build.TOOLS.exists(), reason="no disc image or disc tools")
def test_repack_is_byte_identical():
    work = ROOT / "work/identity"  # not tmp_path: 1.4 GB, and the repo's drive has the room
    shutil.rmtree(work, ignore_errors=True)
    try:
        build.dump(work)
        build.pack(work, work / "out.bin")
        assert filecmp.cmp(ORIG, work / "out.bin", shallow=False)
    finally:
        shutil.rmtree(work, ignore_errors=True)
