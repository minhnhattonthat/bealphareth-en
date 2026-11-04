; vwf.asm: variable-width English in the game's text engine (docs/re/vwf.md). Assembled by tools/build.py with armips.
; Pens are in pixels: 0x28(sp) (line x) and $s7 (x inside the current 48 px text block) were 6 px half-cells.
.psx

FONT_RES equ 0x801B9000            ; RES#3927 in RAM; part 0 = half-width font at +0x14 (cells c-0x21, 11 bytes each)
WIDTHS   equ FONT_RES + 0x14 + 94*11 + 2   ; 95 advances, overwriting unused half-width kana cells
RESIDENT equ WIDTHS + 96           ; code, same area (cells end at FONT_RES+0xBFC)
BLOCK    equ 48                    ; px per text block
NARROW_MAX equ 8                   ; widest VWF advance
RETURN_NEXT equ 0x8004F360         ; after the pen moved: wait, flush test, next char
FLUSH    equ 0x8004F480            ; end the block
KANA_PATH equ 0x8004F23C           ; original one-byte path (kana modes)

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

; --- 0x80050A8C finds a bank's base id after its offset table: M2 only, English can turn a bank into an M4 of strings -------
.org 0x80050AB4
    j     m_head
    nop

.close

; --- resident code, in RES#3927 (loaded at 0x801B9000, always there while text draws) ----------------------------------
.open "FONTRES", FONT_RES
.org WIDTHS
.incbin "vwf_widths.bin"
.org RESIDENT
.area FONT_RES + 0xBFC - RESIDENT

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
    la    t0, WIDTHS - 0x20
    addu  t0, t0, a1
    lbu   t4, (t0)
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

; a0 = one-byte code
vwf_measure_char:
    la    v0, WIDTHS - 0x20
    andi  a0, a0, 0xFF
    addu  v0, v0, a0
    lbu   v0, (v0)
    j     0x80050880
    addu  v0, s2, v0

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
.endarea
.close
