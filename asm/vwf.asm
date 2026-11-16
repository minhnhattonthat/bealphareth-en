; vwf.asm: variable-width English in the game's text engine (docs/re/vwf.md). Assembled by tools/build.py with armips.
; Pens are in pixels: 0x28(sp) (line x) and $s7 (x inside the current 48 px text block) were 6 px half-cells.
.psx

FONT_RES equ 0x801B9000            ; RES#3927 in RAM; part 0 = half-width font at +0x14 (cells c-0x21, 11 bytes each)
WIDTHS   equ FONT_RES + 0x14 + 94*11 + 2   ; 95 advances, overwriting unused half-width kana cells
RESIDENT equ WIDTHS + 96           ; code, same area (cells end at FONT_RES+0xBFC)
BLOCK    equ 48                    ; px per text block
NARROW_MAX equ 8                   ; widest VWF advance
HALF     equ 6                     ; half-width cell after {0e}; fonts/vwf.txt digits are 6 ('1' 4, centred)
WIDE_WORDS equ 10                  ; trap label field in 32-bit words: 80 px, its box shows 76
RETURN_NEXT equ 0x8004F360         ; after the pen moved: wait, flush test, next char
FLUSH    equ 0x8004F480            ; end the block
KANA_PATH equ 0x8004F23C           ; original one-byte path (kana modes)
SUB_RAM  equ 0x80136C00            ; a sub-scene's load address
SUB_POOL_RAM equ 0x801974C0        ; insert.SUB_POOL_RAM
SUB_POOL_MAGIC equ 0x424F5046      ; insert.SUB_POOL_MAGIC

.open "MAIN.EXE", 0x80010000 - 0x800

; --- draw loop 0x8004EBE0 -------------------------------------------------------------------------------------------
; a new block's sprite x is the pen itself
.org 0x8004EE00
    move  v0, v1
    nop

; flush a block once the widest glyph may not fit
.org 0x8004EE2C
    slti  v0, s7, BLOCK - NARROW_MAX + 1
.org 0x8004F450
    slti  v0, s7, BLOCK - NARROW_MAX + 1

; auto-wrap: pen against the box width in half-cells
.org 0x8004EE74
    jal   vwf_wrap
    nop

; one-byte glyphs go to the VWF; two-byte glyphs need 12 px in the block
.org 0x8004F21C
    nop
    j     vwf_char
    nop
    slti  v0, s7, BLOCK - 12 + 1
    beqz  v0, FLUSH
    sll   v0, a1, 0x18

; {0e}: the pen snaps to the 6 px grid (half_on)
.org 0x8004EF34
    j     half_on

; the kana path moves the pen in px
.org 0x8004F284
    addiu v0, v1, 6
.org 0x8004F294
    addiu v1, s7, 6
.org 0x8004F2C0
    addiu v0, v1, 12
.org 0x8004F344
    addiu v0, v1, 12
.org 0x8004F350
    addiu v1, s7, 12

; --- glyph copy 0x8004F854: a0 block, a1 px, a3 width, 0x10(sp) source stride in px, 0x14(sp) source (4bpp) ------------
.org 0x8004F854
.area 0x8004F920 - 0x8004F854
    lw    t3, 0x14(sp)
    lh    t2, 0x10(sp)
    addiu t0, zero, 11
    sra   t2, t2, 1
@@row:
    move  t1, zero
@@px:
    srl   v0, t1, 1
    addu  v0, t3, v0
    lbu   v0, (v0)
    andi  v1, t1, 1
    beqz  v1, @@even
    nop
    srl   v0, v0, 4
@@even:
    andi  v0, v0, 0xF
    beqz  v0, @@next
    addu  v1, a1, t1
    andi  t4, v1, 1
    beqz  t4, @@low
    srl   v1, v1, 1
    sll   v0, v0, 4
@@low:
    addu  v1, a0, v1
    lbu   t4, (v1)
    nop
    or    t4, t4, v0
    sb    t4, (v1)
@@next:
    addiu t1, t1, 1
    bne   t1, a3, @@px
    nop
    addiu t0, t0, -1
    addiu a0, a0, 0x18
    bgtz  t0, @@row
    addu  t3, t3, t2
    jr    ra
    nop
.endarea

; --- half-width painter 0x800313AC: 8 px per row, not 6 (the fixed-cell label drawers use it) -------------------------
.org 0x800313AC
.area 0x800314B0 - 0x800313AC
    andi  a1, a1, 0xFFFF
    mult  a1, a2
    mflo  a1
    blez  a2, @@done
    addu  a0, a0, a1
    lbu   t2, 0x19C(gp)
    lbu   t3, 0x19D(gp)
@@row:
    lbu   t0, (a0)
    addiu a0, a0, 1
    addiu t1, zero, 4
@@byte:
    move  v1, zero
    andi  v0, t0, 0x80
    beqz  v0, @@p2
    andi  v0, t0, 0x40
    move  v1, t2
@@p2:
    beqz  v0, @@p3
    nop
    addu  v1, v1, t3
@@p3:
    sb    v1, (a3)
    sll   t0, t0, 2
    addiu t1, t1, -1
    bgtz  t1, @@byte
    addiu a3, a3, 1
    addiu a2, a2, -1
    bnez  a2, @@row
    nop
@@done:
    jr    ra
    move  v0, zero
.endarea

; --- measure 0x80050798: count px, return half-cells rounded up ---------------------------------------------------------
; a printed variable comes back in half-cells
.org 0x80050810
    j     vwf_measure_var
    nop
; one-byte glyph
.org 0x80050878
    nop
    j     vwf_measure_char         ; delay slot: the `sll v0,v0,16` at 0x80050880, harmless, the helper sets v0
.org 0x80050894
    addiu v0, s2, 12
; result
.org 0x800508F4
    j     vwf_measure_ret
    lw    s4, 0x20(sp)

; --- name labels (HUD, party, status): 8 px VRAM cell per letter becomes one proportional 48 px field per name -----------
; every site: paint into a scratch cell, compose into the name's own buffer, upload the whole field, no step per letter
.org 0x8003A2E0
    addiu v1, zero, 12
.org 0x8003A354
    jal   vwf_paint
.org 0x8003A360
    jal   label_hud
.org 0x8003A370
    nop
.org 0x8003A3BC
    addiu v0, zero, 48

.org 0x8003C774
    addiu v0, zero, 12
.org 0x8003C80C
    jal   vwf_paint
.org 0x8003C818
    jal   label_party
.org 0x8003C824
    nop
    nop
.org 0x8003C850
    addiu v1, zero, 48

.org 0x8003DD9C
    addiu v1, zero, WIDE_WORDS * 2
.org 0x8003DE10
    jal   vwf_paint
.org 0x8003DE1C
    jal   label_status
.org 0x8003DE2C
    nop
    nop
.org 0x8003DE5C
    addiu v1, zero, WIDE_WORDS * 8

; --- text speed: frames per glyph, normal 3 and slow 5 in Japanese. English has about twice the glyphs per line. --------------
.org 0x8004ED14
    addiu v1, zero, 3
    addiu v1, zero, 2
.org 0x8004F17C
    addiu v1, zero, 3
    addiu v1, zero, 2
.org 0x8004F504
    addiu v1, zero, 3
    addiu v1, zero, 2

; --- big outlined text 0x8006C804 (Profile page, issue #1): one 13 px cell a letter. ASCII takes the VWF cells and widths.
.org 0x8006C964
    jal   big_glyph
    lw    a2, 0x4B0(gp)
    nop
.org 0x8006C970
    j     big_advance
    nop
; its half-width unpacker (only English reaches it) skips the 1 px bold: the outline pass already thickens the VWF cells
.org 0x8006D568
    move  v0, zero
; its painter 0x8006D69C writes VRAM unclipped: a letter past screen x 320 lands on the hero portrait (VRAM 320,256).
; Both unpack paths meet here; big_clip masks the 16x16 cell's columns at x >= 319 before the outline and colour passes.
.org 0x8006D81C
    jal   big_clip                 ; does the `move a1, s0` it replaces
; Profile page columns: equipment icon and name 12 px right of the labels, which run past the kanji's 3 cells
.org 0x8006BF00
    addiu a0, s1, 0x44             ; name, was 0x38
.org 0x8006BF0C
    addiu a0, s1, 0x44             ; -Not Equipped- (s1 - 12), was 0x38
.org 0x8006BFC4
    addiu s1, s1, 0x34             ; icon, was 0x28
; Status grid (Equip window) layout records {x, y, 0, 0, id} at 0x80097C9C, x relative to the window: stat labels 4 px
; left so Atk/Def clear a 2-digit number (numbers stay), equipment labels and values 10 px left: item names get 113 px
; before the frame at 304 (D21; the equip screen's list holds 111). MP/Def's ` %3d` field ends at 120 (6 px cells after
; {0e}), 6 px before Mail/Gear.
.org 0x80097C9C
    .halfword 30                   ; HP, was 34
.org 0x80097CA8
    .halfword 80                   ; MP, was 84
.org 0x80097CB4
    .halfword 30                   ; Atk
.org 0x80097CC0
    .halfword 80                   ; Def
.org 0x80097CCC
    .halfword 126                  ; Arms, was 136
.org 0x80097CD8
    .halfword 126                  ; Mail
.org 0x80097CE4
    .halfword 126                  ; Gear
.org 0x80097D20
    .halfword 156                  ; equipped item, was 166
.org 0x80097D2C
    .halfword 156
.org 0x80097D38
    .halfword 156
; Equip screen: left panel (16,39) shows each slot's item under its label, right panel lists items with icon and count
; (count fixed near the right edge, x 287). Names at the labels' x 8 (were 16), left panel 3 px narrower, list panel
; 7 px left with one more column: both hold 111 px. Its stat labels 3 px left so Atk/Def clear a 2-digit number.
.org 0x80097DD4
    .halfword 39                   ; HP, was 42
.org 0x80097DE0
    .halfword 81                   ; MP, was 84
.org 0x80097DEC
    .halfword 39                   ; Atk
.org 0x80097DF8
    .halfword 81                   ; Def
.org 0x80097E64
    .halfword 8
.org 0x80097E70
    .halfword 8
.org 0x80097E7C
    .halfword 8
.org 0x80097E88
    .halfword 8
.org 0x800A0FAC
    .halfword 121                  ; panel width, was 124
.org 0x800A0FB4
    .halfword 112                  ; name box width, was 110
.org 0x800A0F74
    .halfword 139                  ; item list panel x, was 146
.org 0x800A0F78
    .halfword 24                   ; its columns, was 23

; Weak/Half/Null rows: labels 12 px left (Exp's numbers end at 155, ink starts 3 px right of x), no colon; elements from
; label + 34 (was 36), each column its word's pen width + 2 (were 20, one kanji each), so Poison's ink ends at 318
.org 0x8006CB40
    addiu s6, v0, 34
.org 0x8006CBDC
    jal   elem_step                ; fp = next column x; ra is on the stack, the delay slot's lw v0 survives
.org 0x8009A650
    .halfword 156
.org 0x8009A658
    .halfword 156
.org 0x8009A660
    .halfword 156

; --- 0x80050A8C finds a bank's base id after its offset table: M2 only, English can turn a bank into an M4 of strings -------
.org 0x80050AB4
    j     m_head
    nop

; --- sub-scene load 0x80027928: a sub-scene's far strings leave its file before the next load lands on them ----------------
.org 0x80027948
    jal   sub_far

; --- load/save info box (builder 0x80037FD0..): line 1 padded to the Japanese width, the box sizes itself from it ----------
.org 0x800380D8
    jal   slot_pad                 ; was strcat(end, " "); fp = the line buffer

.close

; --- resident code, in RES#3927 (loaded at 0x801B9000, always there while text draws) ----------------------------------
.open "FONTRES", FONT_RES
.org WIDTHS
.incbin "vwf_widths.bin"
.org RESIDENT
.area FONT_RES + 0xBFC - RESIDENT

; the load, then a file ending in [pool, magic, pool length] (insert.sub_pool) copies its pool to SUB_POOL_RAM
sub_far:
    addiu sp, sp, -0x18
    sw    ra, 0x14(sp)
    jal   0x8002770C
    nop
    la    t0, SUB_RAM
    lw    t1, 4(t0)                ; size_total
    nop
    addu  t1, t1, t0
    lw    t2, -8(t1)
    li    t3, SUB_POOL_MAGIC
    bne   t2, t3, @@done
    lw    t2, -4(t1)
    la    t4, SUB_POOL_RAM
    subu  t1, t1, t2
    addiu t1, t1, -8
@@copy:
    lbu   t3, 0(t1)
    addiu t2, t2, -1
    addiu t1, t1, 1
    sb    t3, 0(t4)
    bgtz  t2, @@copy
    addiu t4, t4, 1
@@done:
    lw    ra, 0x14(sp)
    addiu sp, sp, 0x18
    jr    ra
    nop

; a1 = one-byte code at (s1). ASCII mode only; the kana modes keep the original path.
vwf_char:
    lui   v0, 0x800A
    lw    v0, 0x1804(v0)
    nop
    lbu   v1, 0x51(v0)
    andi  a1, a1, 0xFF
    andi  v1, v1, 3
    beqz  v1, @@ascii
    andi  v0, s3, 1
    bnez  v0, @@kana
    slti  v0, s7, BLOCK - 12 + 1
    beqz  v0, @@flush
    nop
@@kana:
    j     KANA_PATH
    addiu a2, zero, 0xB
@@flush:
    j     FLUSH
    nop
@@ascii:
    addiu t0, zero, 0x7F           ; `7F n`: move the pen n-0x20 px (name entry grid, asm/name_grid.asm)
    bne   a1, t0, @@glyph
    lbu   t4, 1(s1)
    addiu s1, s1, 2
    b     @@advance
    addiu t4, t4, -0x20
@@glyph:
    la    t0, WIDTHS - 0x20
    addu  t0, t0, a1
    lbu   t4, (t0)
    andi  v0, s3, 1                ; {0e}: spaces and digits take the Japanese 6 px half-width cell (padded numbers)
    beqz  v0, @@prop
    addiu v0, a1, -0x30
    sltiu v0, v0, 10
    bnez  v0, @@cell
    addiu v1, zero, 0x20
    bne   a1, v1, @@prop
    nop
    b     @@prop
    addiu t4, zero, HALF           ; a space
@@cell:                            ; a digit, centred ('1' is 4 px)
    addiu v0, zero, HALF
    subu  v0, v0, t4
    sra   v0, v0, 1
    addu  s7, s7, v0
    lw    v1, 0x28(sp)
    addiu t4, zero, HALF
    subu  t4, t4, v0
    addu  v1, v1, v0
    sw    v1, 0x28(sp)
@@prop:
    addiu t0, zero, 0x20
    beq   a1, t0, @@advance
    addiu s1, s1, 1
    addiu a1, a1, -0x21
    sll   v0, a1, 3                ; * 11
    addu  v0, v0, a1
    addu  v0, v0, a1
    addu  v0, v0, a1
    lw    t1, 0x8E4(gp)
    lbu   t6, 0x19C(gp)
    addu  t1, t1, v0
    lbu   t7, 0x19D(gp)
    move  t2, s5
    addiu t3, zero, 11
@@row:
    lbu   t8, (t1)
    addiu t1, t1, 1
    sll   t8, t8, 24
    move  t0, s7
@@px:
    beqz  t8, @@rownext
    srl   v0, t0, 1
    bgez  t8, @@skip
    addu  v0, t2, v0
    lbu   t9, (v0)
    andi  v1, t0, 1
    beqz  v1, @@low
    or    a1, t9, t6
    or    a1, t9, t7
@@low:
    sb    a1, (v0)
@@skip:
    sll   t8, t8, 1
    j     @@px
    addiu t0, t0, 1
@@rownext:
    addiu t3, t3, -1
    bgtz  t3, @@row
    addiu t2, t2, 0x18
@@advance:
    lw    v0, 0x28(sp)
    addu  s7, s7, t4
    addu  v0, v0, t4
    j     RETURN_NEXT
    sw    v0, 0x28(sp)

; v0 = box width in half-cells, returns v0 = pen is still inside
vwf_wrap:
    lw    v1, 0x28(sp)
    sll   a0, v0, 1
    addu  v0, v0, a0
    sll   v0, v0, 1
    jr    ra
    slt   v0, v1, v0

; v0 = variable's width in half-cells
vwf_measure_var:
    sll   a0, v0, 1
    addu  v0, v0, a0
    sll   v0, v0, 1
    j     0x80050880
    addu  v0, s2, v0

; a0 = one-byte code; s1 = 0 after {0e}: spaces and digits 6 px, as the draw takes them
vwf_measure_char:
    la    v0, WIDTHS - 0x20
    andi  a0, a0, 0xFF
    addu  v0, v0, a0
    bnez  s1, @@own
    lbu   v0, (v0)
    addiu v1, a0, -0x30
    sltiu v1, v1, 10
    bnez  v1, @@half
    addiu v1, zero, 0x20
    bne   a0, v1, @@own
    nop
@@half:
    addiu v0, zero, HALF
@@own:
    j     0x80050880
    addu  v0, s2, v0

; {0e} (half-width on): the pen goes up to the next 6 px. Callers pad a field with half-width spaces counted from a
; measure that rounds the English up to half-cells (shop prices: name, then W - name - digits spaces), so the field
; lines up on that grid as in Japanese. 0x8004F444 then flushes a block past 40 px.
half_on:
    lw    v0, 0x28(sp)
    addiu t0, zero, 6
    div   v0, t0
    mfhi  v1
    nop
    beqz  v1, @@done
    subu  v1, t0, v1
    addu  v0, v0, v1
    sw    v0, 0x28(sp)
    addu  s7, s7, v1
@@done:
    j     0x8004F444
    nop

; s2 = px; lw s4 already done
vwf_measure_ret:
    addiu v0, s2, 5
    addiu a0, zero, 6
    div   v0, a0
    mflo  v0
    lw    ra, 0x24(sp)
    j     0x800508FC
    nop

; v1 = width byte ('2' or '4'), a0 = n, s0 = bank: the word after an M2's or M4's offset table (the bank's base id)
m_head:
    addiu v1, v1, -0x32
    srl   v0, v1, 1
    addiu v0, v0, 1
    sllv  v0, a0, v0
    addiu v0, v0, 6
    addu  v0, v0, v1
    j     0x80050ACC
    addu  v0, s0, v0

; big text: s0 = code, s2 = full-width flag ({0e} clears it), s3 = mode (0 ASCII). An ASCII byte draws the half-width cell.
big_glyph:
    move  a3, s2
    bnez  s3, @@go
    sltiu v0, s0, 0x80
    beqz  v0, @@go
    nop
    move  a3, zero
@@go:
    j     0x8006D69C
    nop

; pen 0x10(sp): an ASCII byte (space too) moves by its VWF width plus 1 px of outline; anything else keeps 13 or 7
big_advance:
    lhu   v0, 0x10(sp)
    bnez  s3, @@cells
    sltiu v1, s0, 0x80
    beqz  v1, @@cells
    lui   v1, hi(WIDTHS - 0x20)
    addu  v1, v1, s0
    lbu   v1, lo(WIDTHS - 0x20)(v1)
    nop
    addu  v0, v0, v1
    j     0x8006C99C
    addiu v0, v0, 1
@@cells:
    bnez  s2, @@full
    nop
    j     0x8006C978
    nop
@@full:
    j     0x8006C984
    nop

; name labels. The painter's cell goes to label_cell instead of the name's buffer.
vwf_paint:
    la    a3, label_cell
    j     0x800317F8
    nop

; HUD: the 0x480 buffer at 0x800A68D0 holds one 48 px field per slot, slot = (rect x - 0x3C0) / 12
label_hud:
    lhu   t2, (a0)
    lbu   t0, -1(s0)
    addiu t2, t2, -0x3C0
    sll   t3, t2, 4
    sll   t2, t2, 3
    addu  t2, t2, t3
    la    t3, 0x800A68D0
    addu  t2, t2, t3
    addiu a2, zero, 6
    j     vwf_label
    move  t1, s3
label_party:
    lbu   t0, -1(s0)
    move  t2, a1
    addiu a2, zero, 6
    j     vwf_label
    move  t1, s4
; the top bar's trap label: one field at (0x3C0, 0xD0). Its 0x180-byte buffer holds 64 px, so it composes here instead.
label_status:
    lbu   t0, (s0)
    la    t2, label_wide
    addiu a2, zero, WIDE_WORDS
    j     vwf_label
    move  t1, s3

; a0 = rect, t0 = code, t1 = letters so far, t2 = this name's buffer (12 rows, 4bpp), a2 = its words a row. Ends in LoadImage.
vwf_label:
    la    t3, label_pen
    sll   a3, a2, 2
    addiu t4, zero, 1
    bne   t1, t4, @@letter
    lw    t5, (t3)
    move  t5, zero
    sll   t4, a3, 1
    addu  t4, t4, a3
    sll   t4, t4, 2
    addu  t4, t4, t2
@@clear:
    addiu t4, t4, -4
    bne   t4, t2, @@clear
    sw    zero, (t4)
@@letter:
    la    t4, WIDTHS - 0x20
    addu  t4, t4, t0
    lbu   t6, (t4)
    srl   t7, t5, 3                ; word
    addu  t6, t5, t6
    sw    t6, (t3)
    andi  t8, t5, 7
    sltu  t4, t7, a2
    beqz  t4, @@send               ; past the field: clipped
    sll   t8, t8, 2                ; nibbles
    addiu v1, a2, -1
    sltu  v1, t7, v1               ; a next word exists in this row
    sll   t7, t7, 2
    addu  t7, t2, t7
    la    t3, label_cell
    addiu t4, zero, 12
@@row:
    lw    t6, (t3)
    lw    t0, (t7)
    sllv  t9, t6, t8
    or    t0, t0, t9
    sw    t0, (t7)
    beqz  t8, @@next
    subu  v0, zero, t8             ; srlv takes the low 5 bits: 32 - shift
    beqz  v1, @@next
    srlv  t9, t6, v0
    lw    t0, 4(t7)
    nop
    or    t0, t0, t9
    sw    t0, 4(t7)
@@next:
    addiu t4, t4, -1
    addiu t3, t3, 4
    bgtz  t4, @@row
    addu  t7, t7, a3
@@send:
    j     0x80090690
    move  a1, t2

; Profile painter, after the unpack: s0 = 16 rows of a 16 px cell (big-endian halfwords, bit 15 = column 0), the cell's
; x = rect x 0x18(sp) + s3. Keep columns below 319 - x: the outline pass grows a pixel one column right, so 319 stays clear.
big_clip:
    lhu   t0, 0x18(sp)
    move  a1, s0
    addu  t0, t0, s3
    addiu t1, zero, 319
    subu  t1, t1, t0               ; columns kept
    slti  t2, t1, 16
    beqz  t2, @@done
    move  t3, zero
    blez  t1, @@mask
    addiu t2, zero, 16
    subu  t2, t2, t1
    ori   t3, zero, 0xFFFF
    sllv  t3, t3, t2               ; the kept columns' bits
@@mask:
    srl   t4, t3, 8
    move  t5, s0
    addiu t6, s0, 32
@@row:
    lbu   t7, (t5)
    lbu   t8, 1(t5)
    and   t7, t7, t4
    and   t8, t8, t3
    sb    t7, (t5)
    sb    t8, 1(t5)
    addiu t5, t5, 2
    bne   t5, t6, @@row
    nop
@@done:
    jr    ra
    nop

; Profile element columns: s0 = element 0-3 (Heat Cold Bolt Poison), s6 = its x. tests/test_insert.py checks the steps
elem_step:
    la    t0, elem_steps
    addu  t0, t0, s0
    lbu   t0, (t0)
    jr    ra
    addu  fp, s6, t0
elem_steps:
    .byte 31, 28, 28, 0

; Save slot line 1 (" {01}1{01}:{01}W..{01}L{01}v{01}.{01}0.."), laid out like the Japanese full-width line:
; "1: Name" left, "Lv.01 00:28" ending SLOT_TEXT half-cells in, then trailing spaces to SLOT_BOX half-cells, so the box is
; 268 px as in Japanese whatever the name. The party line below centres on it ({0e} spaces, 6 px each). The leading
; space draws 12 px (full-width) but measures 4: SLOT_TEXT 40 puts the time's ink at x 275, as the Japanese.
SLOT_TEXT equ 40
SLOT_BOX  equ 44
slot_pad:
    addiu sp, sp, -24
    sw    ra, 16(sp)
    sw    s0, 20(sp)
    move  a0, fp
    jal   slot_find
    li    a1, 0x3A01               ; "{01}:"
    beqz  v0, @@nocolon
    nop
    jal   slot_ins                 ; "1: Weld"
    addiu a0, v0, 2
@@nocolon:
    move  a0, fp
    jal   slot_find
    li    a1, 0x2001               ; last "{01} ": before the time
    beqz  v1, @@notime
    nop
    jal   slot_ins                 ; "Lv.01  00:28"
    addiu a0, v1, 2
@@notime:
    move  a0, fp
    jal   slot_find
    li    a1, 0x4C01               ; last "{01}L": Lv
    bnez  v1, @@mid
    move  s0, v1
    move  s0, t0                   ; no Lv: pad at the end
@@mid:
    jal   slot_fill
    li    a1, SLOT_TEXT
    move  a0, fp
    jal   slot_find                ; t0 = the NUL
    li    a1, 0
    move  s0, t0
    jal   slot_fill
    li    a1, SLOT_BOX
    lw    ra, 16(sp)
    lw    s0, 20(sp)               ; load delay: ra is ready by jr (DuckStation/hardware honour it, Redux's dynarec doesn't)
    jr    ra
    addiu sp, sp, 24

; insert spaces at s0 until fp measures a1 half-cells
slot_fill:
    addiu sp, sp, -24
    sw    ra, 16(sp)
    sw    a1, 20(sp)
@@loop:
    move  a0, fp
    move  a1, zero
    move  a2, zero
    jal   0x80050700               ; measure, half-cells
    move  a3, zero
    lw    a1, 20(sp)
    nop
    slt   v0, v0, a1
    beqz  v0, @@done
    nop
    jal   slot_ins
    move  a0, s0
    b     @@loop
    nop
@@done:
    lw    ra, 16(sp)
    nop                            ; load delay
    jr    ra
    addiu sp, sp, 24

; a0 = string, a1 = two bytes (low first): v0 = first match, v1 = last match (0 if none), t0 = the NUL. Leaf.
slot_find:
    move  v0, zero
    move  v1, zero
    move  t0, a0
@@loop:
    lbu   t1, (t0)
    lbu   t2, 1(t0)
    beqz  t1, @@done
    sll   t2, t2, 8
    or    t1, t1, t2
    bne   t1, a1, @@next
    nop
    bnez  v0, @@last
    move  v1, t0
    move  v0, t0
@@last:
@@next:
    b     @@loop
    addiu t0, t0, 1
@@done:
    jr    ra
    nop

; insert a space at a0, moving [a0, NUL] one byte right. Leaf.
slot_ins:
    move  t0, a0
@@end:
    lbu   t1, (t0)
    nop
    bnez  t1, @@end
    addiu t0, t0, 1
    addiu t0, t0, -1               ; t0 = the NUL
@@shift:
    lbu   t1, (t0)
    nop
    sb    t1, 1(t0)
    bne   t0, a0, @@shift
    addiu t0, t0, -1
    li    t1, 0x20
    jr    ra
    sb    t1, (a0)

label_pen:
    .word 0
label_cell:
    .fill 0x30
label_wide:
    .fill WIDE_WORDS * 4 * 12
.endarea
.close
