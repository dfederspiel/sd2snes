---
name: port
description: Guide for porting snescom assembly code to 64tass. Use when translating code between snes/ and snes-64tass/, or when hitting 64tass build errors.
argument-hint: "[filename.a65]"
---

# snescom → 64tass Porting Guide

Use this when translating code from `snes/` (snescom) to `snes-64tass/` (64tass).

## Syntax Conversion Table

| snescom | 64tass | Notes |
|---------|--------|-------|
| `#define FOO $1234` | `FOO = $1234` | Constants (no preprocessor) |
| `.byt $xx, $yy` | `.byte $xx, $yy` | Byte data |
| `.byt "text", 0` | `.text "text"` then `.byte 0` | String + null (or `.null "text"`) |
| `.word value` | `.word value` | Same |
| `@label` / `@$addr` | Auto-selected (24-bit if > $FFFF) | Long addressing |
| `!label` / `!$addr` | Auto-selected (16-bit if < $10000) | Absolute addressing |
| `#^label` | `#label >> 16` | Bank byte |
| `#!label` | `#label & $ffff` | 16-bit address portion |
| `.link page $C0` | `* = $C00000` | Set program counter |
| `sep #$20 : .as` | `sep #$20` newline `.as` | No `:` chaining |
| `rep #$10 : .xl` | `rep #$10` newline `.xl` | No `:` chaining |
| `- bra -` | `- bra -` | Same (anonymous labels work) |
| `jmp @label` | `jml label` | Long jump (or auto if cross-bank) |

## Include Model

snescom uses a separate linker step (sneslink). 64tass is single-pass with `.include`:

```asm
; 64tass main.a65 — include everything, no linker needed
.cpu "65816"
.include "memmap.i65"      ; constants
.include "dma.i65"         ; macros
* = $C00000                ; ROM start
; ... code ...
.include "reset.a65"       ; NMI/IRQ handlers
.include "header.a65"      ; ROM header + vectors at $FFB0-$FFFF
.fill $C10000 - *, $00     ; pad to 64KB
```

**Include order matters**: define labels before referencing them. Put handler code (reset.a65) before header.a65 which references the vectors.

## Data Bank Tracking — The Big Difference

This is the most important difference from snescom. 64tass tracks the data bank register and **errors** when an absolute address doesn't match the current bank.

### Rules

1. **After RESET**: DBR=$00. Declare `.databank 0` at top of code.
2. **After `lda #$7e / pha / plb`**: Declare `.databank $7e`.
3. **In NMI/IRQ handlers**: Use `.databank ?` (DBR unknown at interrupt time).
4. **In subroutines**: Declare `.databank N` matching what the caller guarantees.

### Common Error: "not a data bank address"

```
main.a65:44:7: error: not a data bank address bits '$2121'
   stz $2121
       ^
```

**Cause**: The assembler thinks DBR != $00, but $2121 is a PPU register in bank $00.
**Fix**: Ensure `.databank 0` is active and runtime DBR is actually $00 at that point.

### PPU/CPU Registers Need Bank $00

PPU registers ($2100-$213F) and CPU registers ($4200-$43FF) ONLY exist in banks $00-$3F. Accessing them with DBR=$7E writes to WRAM, not hardware!

**Pattern**: Do all hardware register init while DBR=$00, then switch to $7E for WRAM:

```asm
GAME_MAIN
  sep #$20
  .as
  .databank 0           ; DBR=$00 from RESET
  stz $4200             ; CPU register — works with DBR=$00
  jsr snes_init         ; all PPU init — works with DBR=$00
  lda #$0f
  sta $2100             ; PPU register — works with DBR=$00
  ; NOW switch to $7E for WRAM access
  lda #$7e
  pha
  plb
  .databank $7e
  stz some_wram_var     ; $7E0027 — works with DBR=$7E
```

### NMI Handler — Long Addressing

NMI fires with unknown DBR. Use `.databank ?` and long addressing for WRAM writes:

```asm
.databank ?
NMI_ROUTINE
  sep #$20
  .as
  lda #$01
  sta $7E0027           ; long addressing (opcode $8F), works with any DBR
  rtl
```

Note: `stz` has NO long addressing mode. In NMI, use `lda #0 / sta $7Exxxx` instead.

## Macro Conversion

```asm
; snescom (cpp macros via #define):
; DMA7 #$01, src, $2118, #size
; (expanded by preprocessor)

; 64tass:
.macro DMA7 mode, src, dest, size
  lda #\mode
  sta $4370
  lda #\dest
  sta $4371
  ldx #\src & $ffff
  stx $4372
  lda #\src >> 16
  sta $4374
  ldx #\size
  stx $4375
  lda #$80
  sta $420b
.endm
```

## Vector Table

Labels are 24-bit in 64tass. Interrupt vectors are 16-bit `.word` entries:

```asm
* = $C0FFE4
  .word NMI_handler & $ffff    ; mask to 16-bit
  .word RESET & $ffff
  .word IRQ_handler & $ffff
```

## ROM Padding

64tass doesn't auto-pad. Explicitly fill to target size:

```asm
.if * < $C10000
  .fill $C10000 - *, $00       ; pad to exactly 64KB
.endif
```

## Porting Workflow

When porting a file from `snes/foo.a65` to `snes-64tass/foo.a65`:

1. Copy the file
2. Convert `#define` → constant assignments
3. Convert `.byt` → `.byte`, string handling
4. Remove `:` chaining (separate into newlines)
5. Replace `@` / `!` / `^` address prefixes
6. Replace `.link page` with `* =` addressing
7. Add `.databank` directives matching runtime DBR state
8. Add `.include` in main.a65 (no separate linker)
9. Build and fix any remaining errors
10. Compare behavior in bsnes against snescom version

## Files Already Ported (Milestone 1)

| File | Status | Notes |
|------|--------|-------|
| memmap.i65 | Done | 177 constants converted |
| dma.i65 | Done | DMA7 macro converted |
| header.a65 | Done | Vectors use `& $ffff` |
| reset.a65 | Done | Minimal NMI stub, `.databank ?` |
| main.a65 | Done | Boot, snes_init, VRAM/CGRAM clear |

## Files To Port (Milestones 2-3)

| File | Priority | Key challenges |
|------|----------|----------------|
| ui.a65 | M2 | hiprint uses print_* WRAM vars |
| font.a65 | M2 | Large data block, `.byt` → `.byte` |
| palette.a65 | M2 | Simple data, easy port |
| dma.a65 | M2 | HDMA setup, 6 channels |
| const.a65 | M2 | HDMA tables, string data |
| pad.a65 | M2 | Joypad reading |
| filesel.a65 | M3 | MCU communication, complex logic |
| menu.a65 | M3 | Menu system, heavy WRAM use |
| data.a65 | M3 | Variable declarations |
