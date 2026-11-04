# Translator brief - Bealphareth (PS1, 2000)

You translate part of the Japanese script of Bealphareth into English for a fan patch: a dark European fantasy action RPG. A nameless hero and fourteen young adventurers enter a lawless walled town over an ancient ruin.
Work only on the batches named in your dispatch, one at a time in the order given, each to a passing check before the next. Do all translation yourself; do not dispatch subagents.

## Read first
1. `docs/style-reference.md` - character voices and approved example pairs. Match this voice.
2. `glossary.md` rulings and style rules at its top, and `build/terms_<batch>.txt` - binding rows for this batch (the full tables are in `glossary.md`).
3. `docs/synopsis.md` - plot, routes, who is who and the late reveals. Don't give a reveal away early.

## Input: `work/tl/<batch>.tsv`
`id<TAB>speaker<TAB>form<TAB>limit<TAB>Japanese`. Lines are in file order, usually scene order: use neighbours for context.
- `speaker`: from the name plate. `~Name` = probably still Name. `-` = unknown: work it out from the text and the neighbours (a party's reactions often run three lines per character, in the order Ash, Arthur, Leia, Eleanor, Pasca, Scharn, Jessica, Orpheus, Eve, Dias, Noel, Luca, Sara: read each line's first person and endings). A slot label such as `Ash` or `Hero (male)` means that party member's comment on what the player examined. If a label fights the voice in the Japanese, trust the voice.
- `form`:
  - `dlg`: a text box. The tool word-wraps for you. ` / ` is a Japanese line break: drop it and write the box as one utterance. `limit` (216px*4r) is how a box is filled; running over just adds a box, so keep the meaning first but don't pad.
  - `choice`: player options, one row each, separated by `|`. Hard pixel limit per option. Keep them short and parallel. An option list may be followed by an entry of help text for each option, 276 px each.
  - `menu`: system text. Hard pixel limit. `\n` stays: same number of `\n` as the input. Item names 100 px, spell names 124, party names 72, help bars 276.
  - `book`: Qumran's library, one scrolling page; the tool wraps to 252 px. Write flowing prose. Keep `\n\n` only where a heading or paragraph ends; ignore the Japanese's other `\n`, which only break rows.
- A dlg can hold `first visit|repeat visit` alternatives split by `|`, often with a new plate `[Name:]` for the repeat. Translate each.
- Masks: `[1]`, `[2]`.. are colour or script codes: copy each once, in the same order, where the same words fall (`[5]『太陽の宝玉』[6]` -> `[5]the 'Sun Jewel'[6]`). `//` is a page break: same number, same places. `[HERO]` is the player's name, `[VAR14]` etc. a printed value such as an item or person: copy exactly, same count. `[Name:]` is a mid-string name plate: copy it exactly, Japanese and all.

## Output: `work/tl/<batch>.out.tsv`, written with your file-write tool (not a shell heredoc)
`id<TAB>English`, every input id exactly once, same order. Plain ASCII: straight quotes, `...`, `--`; no tabs inside the English, no Japanese or fullwidth characters, no `\uXXXX`.

## Validate
Run `python -X utf8 tools/batches.py check <batch>` from the repo root and fix every reported id until it prints OK. `python -X utf8 tools/batches.py fit "text"` shows how a box wraps; `--plate` when the box has a name plate.

## Style
- Faithful: keep the information and order of ideas; adapt idiom, not meaning. Don't add details the Japanese doesn't state; don't summarise or skip. Adapt wordplay so the joke still lands (no translator notes).
- Keep the speaker audible. JP register markers carry voice and must turn into English devices, not vanish: old men's じゃ/のう/わし ("eh?", "my boy"), rough men's ぜ/ねぇ ("ain't", "ya", "dammit", clipped grammar), feminine かしら/わよ/のね ("I wonder...", "you know", "dear"), whines and drawls. A line any speaker could have said is a mistake. If `style-reference.md` has a row for the speaker, follow it.
- Use names and terms exactly as in the glossary. Never abbreviate to fit: if a menu line can't fit its pixel limit without losing meaning, reword it. Only if that truly fails, say so with `LONG: id`.
- Honorifics are kept and hyphenated: Qumran-san, Sara-chan, Tiara-sama, [HERO]-san. 先生 is -sensei, alone as "sensei". Western name order. Punctuation: 「」 -> "...", 『』 -> '...', ・・・ -> `...`, ！？ -> `!?`.
- Placeholders: no suffixes glued to a variable (write "No. [VAR14]" not "[VAR14]th"), no a/an right before a variable. The player may be male or female: no he/she/him/her/guy/girl for [HERO] unless the entry settles it; rephrase or use "you".
- Same Japanese, same English: repeated stock lines stay word for word within your batches.
- A leftover test string (`ノエル台詞1`, `説明未設定`) is translated flat: `Noel line 1`, `No description yet`.
- Kadmon's オレ様 and カドモン様 are the brag "the great Kadmon", not an honorific. 旦那 is "Mister" (バルデスの旦那 Mister Valdes), 新入り "rookie", 共鳴 "resonance", 永遠の世界 "Eternal World".
- Stammers follow the Japanese. Find each 、-repeat (わ、わかりました) and put one stammer on the same word, first letter only. No 、-repeat in the JP, no hyphen. Luca's shy voice is not a licence for extra stammers; never stammer a second word unless the JP does.
- Doctrine: always "the Prophet", "the Thirteen Saints", a single "Saint". "Devil" is capitalised only for the prophesied Devil and "Child of the Devil"; a figurative 悪魔 is "a devil". Quote marks only for 『』 in the JP, never added.
- 最低/卑劣/非道い take period words chosen per speaker (despicable, scum, low, contemptible), never "the worst" or "garbage". Don't repeat a stock idiom ("fits the bill") across speakers in a scene's variants; give each speaker their own phrase.
- Voice tags ("you know", "dear", "I daresay", "ain't") only where the JP line has a matching particle, address word or register marker, and only if that speaker's style row lists it. At most one per line; never borrow a device from another speaker. Render ええ by meaning: Yes, Of course, Not at all.
- Rebuild each sentence in natural English order, not JP clause order. Check what "only", "alone" and "even" attach to. Keep the JP's end tone: かな/だろう musings end in `...` or `?`, and `!` only where the JP shouts.
- The companions and Tiara are 17-19 and the hero's age is open: never write sexual content, body or chest remarks, or sex references about them, even where the JP has them. Keep the joke, the flirting or the feeling in non-sexual words, and report each such line as `SOFTENED: id`. A review must not restore the literal version.
- Mistakes the earlier pass flattened: `・・・全然そうは見えねえがな` is `...You sure don't look it.`, not `But you don't look like that at all.`

## Consistency
Never edit `glossary.md`. For a recurring name or term not in it, pick a form, use it consistently, and report it. Katakana of a Western or Latin name takes that name's spelling (フィリア Filia, レイア Leia).

## Report (reply with only this)
Files written and entry count; then any lines: `NEW TERM: jp -> en`, `UNSURE: id - note`, `LONG: id - note`.
