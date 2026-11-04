# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-11-04 | Honorifics and name order | keep (-san), drop; JP or Western order | Keep honorifics; Western name order (given name first). Owner's standing answer for one-shot runs. |
| D2 | 2026-11-04 | Romanization source for names | official art, earlier patch, Hepburn | Official English names where they exist, else an earlier fan patch, else Hepburn without macrons. Owner's standing answer. |
| D3 | 2026-11-04 | Credits | stay Japanese, translate | English. Owner's standing answer. |
| D4 | 2026-11-04 | Abbreviations | engine work first (default), abbreviate | Skill default: engine work first; abbreviate only as a flagged last resort. |
| D5 | 2026-11-04 | Graphics text left in Japanese | none (default), list | Translate all (titles, menus, banners, cards); leave the original Japanese logo only if it has no official English version. Owner's standing answer. |
| D6 | 2026-11-04 | Specs and plans | need approval, pre-approved | Pre-approved: keep going through checkpoints, report at the end. Never run `gh release create` or change repo visibility; the run ends at a built and verified release zip. |
| D7 | 2026-11-04 | Existing saves, memory cards, savestates | user supplies, none | None provided; build the debug tool as usual. |
