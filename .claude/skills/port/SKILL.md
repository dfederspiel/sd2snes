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
| `inc` (accumulator) | `inc a` | 64tass requires explicit `a` operand |
| `dec` (accumulator) | `dec a` | 64tass requires explicit `a` operand |

## Include Model

snescom uses a separate linker step (sneslink). 64tass is single-pass with `.include`:

```asm
; 64tass main.a65 — include everything, no linker needed
.cpu "65816"
.include "memmap.i65"      ; constants
.include "dma.i65"         ; macros
.include "data.i65"        ; WRAM variable addresses
* = $C00000                ; ROM start
; ... code ...
.include "ui.a65"          ; text renderer
.include "dma.a65"         ; HDMA setup
.include "font.a65"        ; font tile data
.include "palette.a65"     ; BGR555 palette
.include "const.a65"       ; HDMA tables, strings
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

NMI fires with unknown DBR. Two strategies:

**Strategy A** — Set DBR=$00 for register access, use long addressing for WRAM:
```asm
.databank ?
NMI_ROUTINE
  sep #$20
  .as
  lda #$00
  pha
  plb
  .databank 0
  sta $2115             ; PPU register — absolute (bank $00)
  lda $7E0025           ; WRAM variable — long addressing (auto-selected)
  lda #$01
  sta $7E0020           ; long store to WRAM
  rtl
```

Note: `stz` has NO long addressing mode. In NMI with `.databank 0`, use `lda #0 / sta $7Exxxx` instead.

**Strategy B** — Set DBR=$7E, use long addressing for registers:
```asm
  lda #$7e
  pha
  plb
  .databank $7e
  lda isr_done          ; absolute — assembler picks $0020
  sta $002100           ; long addressing for PPU register
```

Our NMI uses Strategy A (DBR=$00) since there are more register writes than WRAM writes.

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

## Porting Gotchas (Lessons Learned)

### WRAM buffer labels are already 24-bit
Labels like `BG1_TILE_BUF = $7EB000` in memmap.i65 are full addresses. Do NOT add `$7E0000 +` when using them as DMA source. `DMA7 $01, BG1_TILE_BUF, $18, $1000` is correct.

### OAM must be moved off-screen, not just cleared
DMA-clearing OAM to zeros puts 128 sprites at position (0,0) with tile 0 — they're visible! Either disable the OBJ layer (`$212C`/`$212D` = `$03` instead of `$13`) or set all sprite Y coordinates to $F0+ (off-screen).

### Color math window needs explicit disable
When the selection bar is hidden (bar_wl=0), the NMI's bar position math produces a small window at the screen edge. Add a check: if bar_wl=0, set window left > right ($2126=1, $2127=0) to disable the window entirely.

### WRAM variable area must be cleared
Low WRAM ($7E:0000-$7E:00FF) must be DMA-cleared at boot. Uninitialized bar_xl/bar_wl produce visible color math artifacts. But do NOT clear past $7E:00FF — the stack lives at $1FFF and clearing it inside a JSR wipes the return address (black screen).

### VRAM must be explicitly cleared
Unlike snescom which may have implicit clearing, 64tass builds need explicit DMA fills to zero VRAM regions. Random tile data renders as garbage characters.

## Port Status

### Milestone 1 — Boot to screen (COMPLETE)
| File | Status | Notes |
|------|--------|-------|
| memmap.i65 | Done | 177 constants converted |
| dma.i65 | Done | DMA7 macro converted |
| header.a65 | Done | Vectors use `& $ffff` |
| reset.a65 | Done | Minimal NMI stub, `.databank ?` |
| main.a65 | Done | Boot, snes_init, VRAM/CGRAM clear |

### Milestone 2 — Gradient + text (COMPLETE)
| File | Status | Notes |
|------|--------|-------|
| data.i65 | Done | WRAM variable addresses as `$7E`-prefixed constants |
| ui.a65 | Done | hiprint Mode 5 text renderer, `.databank $7e` |
| dma.a65 | Done | HDMA setup (6 channels), killdma |
| font.a65 | Done | 4096 bytes 2bpp tile data (`.byt` → `.byte`) |
| palette.a65 | Done | 512 bytes BGR555 palette |
| const.a65 | Done | HDMA tables, gradient, strings |
| reset.a65 | Expanded | Full NMI: tile DMA, bar positioning, brightness fade |
| main.a65 | Expanded | setup_gfx, genfonts, video_init, poc_display, emu_mode |

### Milestone 3 — Input + sprites (NEXT)
| File | Priority | Key challenges |
|------|----------|----------------|
| pad.a65 | High | Joypad reading — enables interaction |
| logo.a65 | Medium | Logo tile data — or create new sprite graphics |
| OAM/sprites | Medium | OAM init, sprite tile loading, position control |
| filesel.a65 | Low | MCU communication — only useful on real hardware |
| menu.a65 | Low | Menu system — depends on filesel |

**Milestone 3 goals**:
- Joypad input (d-pad, buttons) with edge detection
- Basic sprite rendering (load tiles, set OAM entries, enable OBJ layer)
- Controllable sprite as a learning exercise
- Selection bar movement driven by joypad (cursor navigation)
