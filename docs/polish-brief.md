# Polish pass brief - Bealphareth

You resolve one chunk of `docs/polish.md`: `work/tl/polish/pNN.md`. Do all of it yourself; no subagents, no git. Never run `batches.py merge`: the controller merges at the end.

Read first: `glossary.md` (rulings), `docs/style-reference.md`, `docs/translator-brief.md` (Style, format), `docs/decisions.md` D11.

For each line of the chunk:
1. Find its strings: `Grep` the id in `work/tl/*.out.tsv` (`b###.out.tsv`, `id<TAB>English`); the JP is in the matching `b###.tsv`. A bare offset like `2683c` is a tail: grep `:2683c<TAB>`. A speaker or JP gist tells twins apart.
2. Judge it against the JP. The suggestion is a proposal, not an order: take it, improve it, or waive it. A line that is fine as it stands is waived. Sexual content stays softened (D11); never restore a softened line to the literal JP.
3. Fix by Edit, line by line, in the `.out.tsv`. No bulk replace, no script writes. Keep `[n]`, `//`, ` / `, `[HERO]`, `[VAR14]` exactly as the batch's other lines of that shape. Same JP, same English: grep the JP gist in `work/tl/b*.tsv` and fix twins too. Refrain lines (same JP) become word for word.
4. Fit: `python -X utf8 tools/batches.py fit "English"` shows the wrapped pages. Names must stay inside their column: item 100 px, spell 124 px, help bar 276 px, and there is no widening. A line that says "if widened" is waived unless it fits as it is.
5. Tick the line in your chunk file with Edit, keeping its text and appending the outcome:
   - `- [x] <line> - fixed`
   - `- [x] <line> - waived: <reason in a few words>`
   - A line that can only be settled by seeing the game ("check in-game", a button icon, a code showing on screen): `- [x] <line> - qa: <what to look at>`.
6. For each batch you touched run `python -X utf8 tools/batches.py check bNNN` until it prints OK.

Glossary or `docs/` changes: do not edit them; put them in your reply. Another agent has neighbouring chunks: if an Edit fails because a file changed, re-read and retry.

Reply in at most six lines: `<chunk>: <n> fixed, <w> waived, <q> qa`, then any glossary rows needed and anything you could not settle.
