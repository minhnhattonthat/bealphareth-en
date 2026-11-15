; name_grid.asm: the name entry grid on the Japanese layout (RES#1023, tools/overlays.py).
; The row builder (0x800D6E9C) made each cell `c {0e} space {0f}`: 18 px a kana cell, 6 more after every 5th, the cursor
; box at 21 + 18*col + 6*(col/5). English rows are built once by overlays.grid_rows (each glyph centred in its cell with
; the VWF's `7F n` pen move) and drawn as they are, so the original cursor code fits them again.
; The page is always 1 (set at 0x800D8304; only 3 <-> 4 toggle), so one set of rows serves.
.psx
.open "RES1023", 0x800D6C00

ROW_LEN equ 46

; s2 = the first row, both page branches
.org 0x800D6E38
    lui   s2, hi(rows)
    addiu s2, s2, lo(rows)
.org 0x800D6E48
    lui   s2, hi(rows)
    addiu s2, s2, lo(rows)

.org 0x800D6E9C
.area 0x800D7000 - 0x800D6E9C
    sw    v0, 0x24(sp)
    sw    v1, 0x28(sp)
    sw    a0, 0x20(sp)
    move  s0, s2
    j     0x800D7000
    addiu s2, s2, ROW_LEN
rows:
    .incbin "name_rows.bin"
.endarea

.org 0x800D7018                    ; the draw call's string
    move  a1, s0
.close
