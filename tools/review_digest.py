"""Roll reviewer reports up: `python -X utf8 tools/review_digest.py` lists batches with no report, every report's
Unresolved items and non-ok assessments, and appends new Minor lines to docs/polish.md (one `- [ ]` line per finding)."""
import glob, os, re

SECTION = re.compile(r"^## (.+)$", re.M)


def sections(path):
    text = open(path, encoding="utf8").read()
    parts = SECTION.split(text)
    return {parts[i].strip().lower(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def main():
    reports = sorted(glob.glob("work/qa/reviews/*.md"))
    pairs = {os.path.basename(p)[:-4] for p in glob.glob("work/qa/pairs/*.txt")}
    print("reports", len(reports), "pairs without report", sorted(pairs - {os.path.basename(r)[:-3] for r in reports}))
    done = open("docs/polish.md", encoding="utf8").read() if os.path.exists("docs/polish.md") else "# Polish\n\n"
    new = []
    for r in reports:
        s = sections(r)
        name = os.path.basename(r)[:-3]
        verdict = s.get("assessment", "MISSING")
        if not verdict.lower().startswith("ok"):
            print(name, "ASSESSMENT", verdict[:200])
        if s.get("unresolved"):
            print(name, "UNRESOLVED", s["unresolved"])
        new += [l for l in s.get("minor", "").splitlines() if l.startswith("- [ ]") and l not in done]
    if new:
        with open("docs/polish.md", "w", encoding="utf8", newline="\n") as f:
            f.write(done.rstrip("\n") + "\n" + "\n".join(new) + "\n")
    print("polish lines added", len(new))


if __name__ == "__main__":
    main()
