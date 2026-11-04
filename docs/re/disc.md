# Disc layout and loading

Disc: one MODE2/2352 track, 706,733,664 bytes. `dumpsxiso` dumps it cleanly (verified: exit 0, 14 files; `work/disc/`).

| File | Size | What it is |
|---|---|---|
| `SYSTEM.CNF` | 68 | `BOOT = cdrom:\SCPS_101.38;1` |
| `SCPS_101.38` | 120,832 | PS-X EXE, 0x80010000, entry 0x80010C88. Boot loader, runs `\PSX.EXE;1` (string at file 0x800). **verified** by string and header |
| `PSX.EXE` | 172,032 | PS-X EXE header (0x800D5000, entry 0x800D6A38), but its bytes also sit in RAM at base **0x801A306C** during play: holds the font and the system message bank (`text.md`). **verified**: `tools/ram_prov.py` matches file 0x15B84.. to RAM 0x801B8BF0.. |
| `MAIN.EXE` | 598,016 | PS-X EXE, 0x80010000, entry 0x80080224, the game. Names `\MAIN.RES;1`, `\STR\START.STR;1`, `\STR\PROLO.STR;1`, `MUSIC0-4.XA;1`. **verified** by RAM match |
| `MAIN.RES` | 203,921,408 | Archive, see below |
| `XA/MUSIC0-4.XA` | 350 MB | Music/XA (mixed sectors) |
| `STR/START.STR`, `STR/PROLO.STR` | 31 MB, 55 MB | FMV. `PROLO.STR` has burned-in Japanese subtitles (`graphics.md`) |
| `DUMMY.180` | 27,648,000 | Zero padding: **27 MB of free disc space** (guess until the rebuild test: keep the file name, shrink it) |

Layout XML from `dumpsxiso -s` includes a 150-sector trailing dummy; `DUMMY.180` is last on disc.

Identity: `dumpsxiso` + `mkpsxiso` with no edits rebuilds the disc byte for byte, no layout tweaks needed. **verified** by `tests/test_identity.py`.

## MAIN.RES (verified by `tools/res.py`, chained offsets fill the file exactly)

```
u32 count (5010), u32 total_size (== file size)
u32 offset[count]   // relative to byte 8; entry data at offset+8, 0x800-aligned; first entry at 0x5000
```
1878 entries are empty (same offset as the next one). Entry classes (first dword, `tools/res_types.py`):

| Class | Count | Index range | Notes |
|---|---|---|---|
| `02 00 00 00` scene overlay | 324 | 1..4126 | Slot 0x40000 (184) or 0xA0000 (140) bytes. Code + assets + text. A map (0xA0000) loads at **0x800D6C00**; a sub-scene (0x40000) loads at **0x80136C00** (both verified by RAM dump, `docs/re/warp.md`) |
| `28/48/68/88/a8/e8/.. 00 00 00` | ~1000 | 365..4548 | u32 palette bytes+8, u32 palette count, 16-colour palettes, then sprite records (`00 80 00 01 00 01 ..` flags, w, h, u32 packed size). Pixel data is compressed |
| `30 00 00 00` | 722 | 366..3957 | Framed sprites paired with the entry before them |
| `00 00 xx xx` + 16-colour palette | ~300 | 2301..2599 | Palette then raw 4bpp map tiles |
| `xx xx 00 38` | 530 | 2216..3212 | **MDEC BS v2 stills** (`u16 size, 0x3800, u16 qscale, u16 version=2`) |
| `M4` | 61 | 1049.., 3927.. | Message banks (`text.md`) |
| `.. SShd` | 50 | 3322.. | VAB sound banks |

## Scene overlay (0x2 entries; verified on #1023 by RAM match at 0x800D6C00, read at 0x8006A2A0)

```
u32 2, u32 size_total, u32 8, u32 sec2_offset
+0x10 code (MIPS) ...
sec2_offset: char name[8]; u32 n; u32 size; u32 off[n]; part k starts at sec2_offset + 16 + off[k]
```
The two offset fields (`size`, `off[]`) and the header's `size_total` must all follow when a message bank grows; a table read one word off left the last part unshifted and crashed the map load (verified: `tools/insert.py`, marker build). Nothing in the code or parts addresses a later part absolutely (`tools/ov_refs.py`, and every scene loads in the marker tour).
Example #1023: size_total 0x84DB4, sec2 at 0x10114 with 31 parts; slot 0xA0000, so 0x1B24F bytes unused on disc.

## Free space

- **Disc:** `DUMMY.180` (27 MB). `MAIN.RES` can grow if the table is rewritten (files are found by name). Entries are read by offset/size from its table (guess until the identity + moved-entry test).
- **Scene slots:** 0x40000 / 0xA0000 per scene, zero-padded. `tools/slack.py` (tsv): tightest slack vs text are #361 (0.16x), #107 (0.44x), #101 (0.52x), #76 (0.60x), #1951 (0.67x); most are above 1x.
- **RAM:** a scene occupies 0x800D6C00 up; PSX.EXE data starts at 0x801A306C, so a scene has at most **0xCC46C bytes**. With #1023 loaded (0x84DB4), RAM after it up to 0x801A3000 is **not all free**: 0x8015B000-0x80170000 and 0x8018B000-0x80197000 held data in the first scene; zero runs at 0x80173000-0x80177000 and 0x8017F000-0x80187000 are candidates only. Trap-test before use.
- **The sub-scene line (phase 8):** as a sub-scene starts, `0x80019A24` loads file 12 over 0x80156C00 and fills to 0x80176C00, which is sub offset 0x20000 and up. Some parts are read after that (`0x8002ACFC` keeps pointers to a part, the animator reads it per frame), so English pushing one across the line reads file 12 as sprite data: on RES#4107 the tavern floor went, then the emulator froze about 3,600 frames later. `insert.LOAD_LINE`: a part that ended below the line stays below it. What does not fit goes to the end of the sub-scene's own file; `sub_far` (`asm/vwf.asm`, hooked on the load at `0x80027948`) copies it to `0x8017EA00` (0x9600 bytes) before the line is hit. Only one sub-scene is loaded at a time, so they share that buffer. Maps have a like line at 0x60000 (a sub-scene over 0x80136C00); nothing has been seen to read past it, `tools/debug/vram_compare.py` is the check.
- **Lowest risk for text growth:** English in 1-byte codes is about twice the Japanese bytes (kana 1, kanji 2). Size per scene must be checked in the build against both slot and RAM.
