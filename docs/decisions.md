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
| D8 | 2026-11-04 | Phase 6 workers | translate alone, Claude Code translator/reviewer subagents | Coordinator: everything is pre-approved, decide. Chose subagents of `.claude/agents/` types: 19,000 entries do not fit one context. Orca workers stay off. |
| D9 | 2026-11-04 | Spelling of names with no official form | strict Hepburn (Kumuran, Reia), the Western name the katakana renders | Western or Hebrew or Latin form when the katakana plainly renders one (Qumran, Leia, Sheol, Eleanor, Dias); D2's Hepburn for the rest. No official or fan English list was found; the guide wiki's page ids (valdes, qumran, fatum) agree. |
| D10 | 2026-11-04 | Unfinished `(仮)` lines in scene tables (RES#27, #38 and others: `Pasca / ghost generator OFF (tentative)`) | translate each, leave Japanese, a neutral line | Draw `...`: 2,430 strings no player should read, not worth 7 batches, and phase 7 wants the space. `(仮)` in `PSX.EXE` spell names stays translated. |
| D11 | 2026-11-05 | Sexual remarks about the 17-19 companions, Tiara and the age-open hero (e.g. RES#327:a673 chest remark, `押し倒したい` lines) | literal, soften | Soften, my call and not a user ruling: the English keeps the joke or feeling in non-sexual words and is deliberately unfaithful there. Lines are logged as `SOFTENED:` in translator reports; no review restores them. |
