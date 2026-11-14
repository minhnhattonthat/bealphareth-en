; name_cursor.asm: name entry cursor x for the proportional English grid (RES#1023, tools/overlays.py).
; The grid row is drawn as one string, each cell `c {0e} space {0f}`; the Japanese cursor sat at 21 + 18*col + 6*(col/5).
; With the VWF a cell is the glyph's advance plus a 4 px space, so the cursor sums the cells before it.
.psx
.open "RES1023", 0x800D6C00

WIDTHS_LESS_20 equ 0x801B9400      ; vwf.asm WIDTHS - 0x20

.org 0x800D7100
    lui   t2, hi(WIDTHS_LESS_20)   ; t1 (col*18) is no longer used
.org 0x800D7108                    ; keep the row in a0
    slti  t5, a0, 6
    beqz  t5, 0x800D7170
.org 0x800D7114
.area 0x800D716C - 0x800D7114
    addiu v1, v0, 0x53             ; v0 = row*16: y, then a 13x13 box
    sh    v1, 0x12(sp)
    addiu v1, zero, 0xD
    sh    v1, 0x16(sp)
    sh    v1, 0x14(sp)
    sll   v1, a0, 4
    subu  v1, v1, a0               ; row*15
    lui   a0, 0x800E
    lw    a0, 0x31E4(a0)           ; the grid (every page is the ASCII table)
    addiu v0, zero, 21
    addu  a0, a0, v1
    addu  t3, a0, a3               ; a3 = col
@@loop:
    beq   a0, t3, @@done
    lbu   t4, 0(a0)
    addiu a0, a0, 1
    addu  t4, t2, t4
    lbu   t4, lo(WIDTHS_LESS_20)(t4)
    addiu v0, v0, 4                ; the space after each cell (VWF advance of 0x20)
    b     @@loop
    addu  v0, v0, t4
@@done:
    j     0x800D71C8
    sh    v0, 0x10(sp)
.endarea
.close
