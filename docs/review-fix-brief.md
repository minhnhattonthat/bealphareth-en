# Review-and-fix brief - Bealphareth

You did not translate these batches. Review them as `docs/reviewer-brief.md` says, then fix what you find. Do all of it yourself; no subagents, no git.

Dispatch: a range name such as `r099` and its batches.

1. Read `docs/reviewer-brief.md`, `docs/style-reference.md`, `glossary.md` (rulings, families, decisions), `docs/synopsis.md`, and `docs/translator-brief.md` (Style).
2. Read the whole pairs file `work/qa/pairs/<range>.txt`, in passes if large. It holds every entry of those batches; `=== bNNN` marks where each starts.
3. Judge each line. Critical = meaning reversed, broken placeholder grammar, wrong speaker, a reveal given away. Important = clear mistranslation, glossary inconsistency, abbreviation, voice flattened or borrowed from another speaker, joke dead, scope error (what "only" or "alone" attaches to), a stammer that does not follow the Japanese, a voice tag with no JP marker. Minor = style only. Be concrete; do not flag taste.
4. Fix every Critical and Important in `work/tl/<batch>.out.tsv` with your edit tool, line by line. Never rewrite a line that is merely fine; no bulk replace. Same JP, same English: fix the twin lines too.
   Sexual content, body or chest remarks, or sex references about the companions, Tiara or the hero (17-19, hero's age open) are Important: reword non-sexually per `docs/decisions.md` D11, keeping the joke or feeling. Never restore a softened line to the literal JP.
5. Run `python -X utf8 tools/batches.py check <batch>` for each batch you touched until it prints OK.
6. Write `work/qa/reviews/<range>.md` with your file-write tool:
```
## Fixed
id - JP gist - old EN -> new EN   (one line each; Critical first)
## Minor
- [ ] id - JP gist - problem - suggested EN
## Unresolved
id - why you could not settle it (speaker unknown is not unresolved unless it changes the meaning)
## Assessment
ok | issue - one sentence
```
Assessment is `ok` once no Critical or Important stays unfixed.

Reply with one line only: `<range>: <n> fixed (<c> critical), <m> minor, <u> unresolved, ok|issue`. Everything else goes in the file.
