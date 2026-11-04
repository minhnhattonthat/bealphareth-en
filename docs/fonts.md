# Fonts

Every font or glyph sheet the build reads ends up inside the released patch, so its licence must allow that. One row
per file; a font with no known licence doesn't go into a release.

| File | Source (URL, version) | Licence | Redistributable in a patch | Used for | Changes made |
|---|---|---|---|---|---|
| fonts/LiberationSerif-Regular.ttf, fonts/LiberationSerif-Bold.ttf | Liberation Fonts 2.1.5, github.com/liberationfonts/liberation-fonts | SIL OFL 1.1, `fonts/LICENSE-Liberation` | yes: OFL allows use in products, and the patch holds rendered pixels only | English on still pages and sheets (`tools/stills.py`) | none |
| fonts/vwf.txt | The game's own 11x11 full-width ASCII cells (`PSX.EXE` 0x16B90), trimmed to their ink by `tools/vwf_font.py init`, then edited by hand | Glyphs already on the player's disc | yes, as patch bytes against the player's own disc | all English text (VWF) | proportional advances; M, W and `-` redrawn |
