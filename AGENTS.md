# Bealphareth (PS1, SCPS-10138) English translation

Skill: translate-retro-game; `python tools/skill.py` prints its folder. Read its SKILL.md before ROM, text or QA work. `"$(python tools/skill.py)"` works in bash and PowerShell; never paste a `plugins/cache/<hash>` path.

After cloning: `git config core.hooksPath tools/hooks`.

## Commands (run from repo root)
- Build:    `python -X utf8 tools/build.py` -> build/bealphareth_en.cue/.bin (checks the dump against `rom.sha1` first; unpacked disc in `work/disc/`).
- Check:    `python -X utf8 tools/check.py` (tests + lint; the pre-commit hook runs this)
- Smoke:    `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/bealphareth_en.cue --out work/qa/smoke --route tools/routes/boot.txt --smoke`
- Warp:     `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" <cue> --out work/qa/scenes/<name> --route tools/routes/newgame.txt --script tools/debug/warp.lua --var "SCENE='<name>'" --frames 7000 --mash-key circle` (`<cue>` is `build/bealphareth_en.cue` once built, else the Japanese disc; scenes: `tools/debug/scenes.lua`; never ask the user to play to a scene).
- Scenes:   `python -X utf8 tools/debug/regen.py` cold-boots all 306 scenes into `work/qa/scenes/result.tsv` (name globs, `--jobs`, `--state` writes savestates); `tools/debug/sheets.py` pages the shots into contact sheets.
- Release:  `python -X utf8 tools/release.py` (patch + verify; never publish without the user). Phase 9.
- Clean:    `python -X utf8 tools/clean.py` (published projects: lists rebuildable/downloadable files; `--yes` deletes)

## Paths
- Original disc: `rom/Bealphareth (Japan).bin` + `.cue` (gitignored; SHA-1 in `rom.sha1`, checked by `tools/check_rom.py`).
- Emulator: PCSX-Redux nightly 30264.20261103.29 in `tools/pcsx/` (`fetch_emu.py pcsx`), BIOS `tools/bios/scph5500.bin` (`fetch_emu.py psx-bios`). Gitignored. Savestates: `work/states/`.
- Disc tools: mkpsxiso/dumpsxiso 2.30 in `tools/mkpsxiso/mkpsxiso-2.30-win64/` (github.com/Lameguy64/mkpsxiso/releases/download/v2.30/mkpsxiso-2.30-win64.zip); armips 0.11.0 in `tools/armips/` (github.com/Kingcom/armips/releases/download/v0.11.0/armips-v0.11.0-windows-x86.7z). Gitignored.
- Text: `script/` (JSON). Tables: `tbl/`. Glossary: `glossary.md`. RE notes index: `docs/re/README.md`. Fonts and their licences: `docs/fonts.md`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- Subagents: dispatch the `.claude/agents/` types (translator, reviewer, visual-qa, playtester), never general-purpose: their short tool list cuts each agent's start-up context from ~43k to ~9k tokens.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Japanese games confirm with circle: `--mash-key circle`.

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
