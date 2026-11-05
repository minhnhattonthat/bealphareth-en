Bealphareth English translation, version {VERSION}

Unofficial fan translation of Bealphareth (PlayStation, SCPS-10138, Sony Computer Entertainment, 2000). No game data is included,
and pre-patched copies are not provided: you need your own dump of the Japanese disc.

PATCHING
Patch the disc's .bin with xdelta3 (https://github.com/jmacd/xdelta) or the Delta Patcher GUI:
    xdelta3 -d -s "Bealphareth (Japan).bin" {PATCH} bealphareth_en.bin
Keep your .cue and point it at the new file, or copy it with the new name.

The base disc must be a single .bin of raw sectors, with these hashes:
    size   {SIZE} bytes
    CRC32  {CRC32}
    MD5    {MD5}
    SHA-1  {SHA1}
The patched disc has CRC32 {NEW_CRC32}, SHA-1 {NEW_SHA1}.

Start a new game after patching. Old savestates hold the old code and font and will misbehave; memory card saves are fine.

TRANSLATION STATUS
Dialogue and story        English
Menus, items, messages    English
Item cards, documents     English (typeset over the original pictures)
Mission cards, endings    English
Prologue video subtitles  English
Title logo                the game's own English logo, katakana removed
Name entry                English letters

KNOWN ISSUES
See https://github.com/minhnhattonthat/bealphareth-en/issues. A few item cards whose pictures hold overlapping developer text were
given a clean description rather than a literal reading.

TESTED ON
PCSX-Redux and DuckStation. Real hardware not tested.

CREDITS
Translation and tools made with AI assistance (Claude), directed by the project owner. Fonts: Liberation Serif (SIL Open Font Licence).
Report bugs through the issues page, with a savestate if you can.
