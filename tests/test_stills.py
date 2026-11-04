"""Still pages: wrapping keeps the row count of a greedy fill, stays in the box and leaves no needless one-word row."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import stills


class Chars:
    getlength = staticmethod(len)


def test_wrap_balances_rows():
    assert stills.wrap("Clothes made of a strange material.", Chars, 18) == ["Clothes made of a", "strange material."]
    assert stills.wrap("A glass tankard.", Chars, 10) == ["A glass", "tankard."]


def test_wrap_keeps_a_long_word_and_forced_lines():
    assert stills.wrap("Attack 18\nA verylongwordindeed here", Chars, 12) == ["Attack 18", "A", "verylongwordindeed", "here"]
