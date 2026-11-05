# Bealphareth English translation

Unofficial English fan translation of **Bealphareth** (PlayStation, Sony Computer Entertainment, 2000): the source text and tools
that build the patch.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| Dialogue / story | English |
| Menus, items, skills, system messages | English |
| Item cards, documents, mission title cards, endings (drawn as graphics) | English |
| Prologue video subtitles | English |
| Name entry | English |

Version 1.0 is out. Tested on PCSX-Redux and DuckStation, not on real hardware. Full battles, shops, the Game Over screen and many later events haven't been played through by hand, so please report anything odd.

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English. Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `tools/` | Python build chain: extract, insert, lint, release. |
| `tests/` | pytest suite (ROM-dependent tests skip when the ROM is absent). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md` | Rulings with their reasons; current progress and open bugs. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |
| `.claude/agents/` | Subagent types (translator, reviewer, visual QA, playtester) with only the tools each needs. |

## Build your own patched ROM

Needs Python 3.12+ and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/bealphareth-en
cd bealphareth-en
git config core.hooksPath tools/hooks
# copy your dump to: rom/Bealphareth (Japan).bin and .cue
#   (.bin: 706733664 bytes, SHA-1 81c2845c671f57f8937748b39ba809ac2c050aaa; the build refuses any other dump, see rom.sha1)
python -X utf8 tools/build.py                          # -> build/bealphareth_en.cue/.bin
python -X utf8 tools/check.py                          # tests + text lint
```

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is Sony Computer Entertainment's and is included only so
the translation can be checked against it. Bealphareth is (c) Sony Computer Entertainment; this project is not affiliated with them.
Do not share patched ROMs.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
