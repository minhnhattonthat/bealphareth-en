"""slack.py: per-scene room in MAIN.RES. For each 0x2-header scene: slot size, used bytes, trailing zero slack, and M2 text bytes (tsv to stdout)."""
import csv
import struct
import sys

import mscan
import res

w = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
w.writerow(["entry", "slot", "used", "slack", "header_total", "text_bytes", "slack_vs_text"])
tot_text = 0
worst = []
for i, o, s, b in res.entries():
    if struct.unpack_from("<I", b, 0)[0] != 2:
        continue
    used = len(b.rstrip(b"\0"))
    total = struct.unpack_from("<I", b, 4)[0]
    text = sum(e - a for _, a, e, _, _ in mscan.banks(b))
    tot_text += text
    w.writerow([i, s, used, s - used, total, text, round((s - used) / text, 2) if text else ""])
    if text:
        worst.append(((s - used) / text, i, s, s - used, text))
worst.sort()
print("# total text", tot_text, file=sys.stderr)
print("# tightest", worst[:10], file=sys.stderr)
