"""pairs.py: reviewer input from translated batches. python -X utf8 tools/pairs.py OUT.txt b005 b006 ...

One entry per line pair, in batch order: `>> id | speaker | form | JP` then `EN`. Batch order is scene order, so neighbours are the context.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402


def pairs(names):
    out = []
    for name in names:
        en = dict(batches.read_out(name) or [])
        out.append(f"=== {name}")
        for r in batches.read_batch(name):
            out.append(f">> {r['id']} | {r['speaker']} | {r['form']} | {r['text']}")
            out.append(en.get(r["id"], "<missing>"))
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[1]).write_text(pairs(sys.argv[2:]), encoding="utf8", newline="\n")
