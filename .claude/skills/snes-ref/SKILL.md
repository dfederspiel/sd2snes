---
name: snes-ref
description: 65816 assembly and SNES PPU reference for the sd2snes menu ROM. Auto-loads when editing .a65 assembly files, working with SNES graphics, palettes, HDMA, or the menu ROM codebase.
---

# sd2snes Menu ROM - Quick Reference

## Assembler Syntax Comparison

### snescom (snes/ directory)

| Syntax | Meaning |
|--------|---------|
| `@label` or `@$addr` | Long (24-bit) address |
| `!label` or `!$addr` | Absolute (16-bit) address |
| `#^label` | Bank byte of label address |
| `#!label` | 16-bit address of label |
| `.as` / `.al` | 8-bit / 16-bit accumulator mode hint |
| `.xs` / `.xl` | 8-bit / 16-bit index register mode hint |
| `sep #$20 : .as` | Set 8-bit A (instruction + mode hint, `:` chains) |
| `.byt` | Define byte(s) |
| `.word` | Define 16-bit word(s) |
| `#define NAME value` | Preprocessor constant (cpp) |
| `.link page $C0` | Set output address/bank |
| `- bra -` | Branch to previous anonymous label |
| `-` / `+` | Anonymous labels (backward / forward) |

### 64tass (snes-64tass/ directory)

| Syntax | Meaning |
|--------|---------|
| `sta $7E0027` | Long addressing auto-selected (addr > $FFFF) |
| `sta $2100` | Absolute addressing auto-selected (addr < $10000) |
| `label >> 16` | Bank byte of label (replaces `#^label`) |
| `label & $ffff` | 16-bit address of label (replaces `#!label`) |
| `.as` / `.al` / `.xs` / `.xl` | Same as snescom |
| `sep #$20` then `.as` on next line | No `:` chaining — separate lines |
| `.byte` | Define byte(s) (NOT `.byt`) |
| `.word` | Define 16-bit word(s) (same) |
| `.text "string"` | Define ASCII text (NOT `.byt "text"`) |
| `NAME = $value` | Constant assignment (replaces `#define`) |
| `* = $C00000` | Set program counter (replaces `.link page`) |
| `.include "file"` | Include source file (no separate linker) |
| `.fill count, value` | Fill bytes |
| `.cpu "65816"` | Set CPU type (required at top) |

### 64tass Data Bank Tracking (CRITICAL)

64tass enforces that absolute addresses match the current data bank register. This catches real hardware bugs (e.g., accessing PPU registers with wrong DBR).

| Directive | When to use |
|-----------|-------------|
| `.databank 0` | After RESET, or when DBR=$00 (PPU/CPU register access) |
| `.databank $7e` | After `lda #$7e / pha / plb` (WRAM variable access) |
| `.databank ?` | NMI/IRQ handlers where DBR is unknown |

**Key rules:**
- PPU registers ($21xx) and CPU registers ($42xx) only exist in banks $00-$3F
- With DBR=$7E, `sta $2100` writes to WRAM $7E2100, NOT the PPU register!
- `stz` has no long addressing mode — must set DBR correctly or use direct page
- In NMI handler, use long addressing: `sta $7E0027` (opcode $8F)
- For vector tables: `.word LABEL & $ffff` (labels are 24-bit in 64tass)

### 64tass Register Size Tracking (CRITICAL)

64tass tracks `.as`/`.al`/`.xs`/`.xl` to determine immediate operand sizes. It does NOT propagate this state across `jsr`/`rts` or `jml` boundaries.

**Every function must declare its register sizes at entry:**
```asm
my_function
  sep #$20          ; also sets CPU state (belt + suspenders)
  .as
  rep #$10
  .xl
```

**Why this matters**: Without `.xl`, `ldy #0` assembles as 2 bytes ($A0 $00) instead of 3 ($A0 $00 $00). If the CPU is actually in 16-bit index mode, it reads an extra byte, misaligning ALL subsequent instructions. This causes silent garbage execution — extremely hard to debug.

**Also required: `.dpage 0`** — Declare once at top of main.a65 for correct indirect long `[dp],y` operand generation. Without it, the assembler generates wrong DP offsets.

**Verification**: hexdump the binary at the function's address (from `--labels` output). Check that `LDY #imm` ($A0) has the right operand width.

### 64tass Macro Syntax

```asm
; snescom:  DMA7 #$01, src, $2118, #size
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

## 65816 Key Instructions

- `sep #$20` = set 8-bit accumulator (M flag)
- `sep #$10` = set 8-bit index (X flag)
- `rep #$20` = set 16-bit accumulator
- `rep #$10` = set 16-bit index
- `rep #$30` = set 16-bit A and X/Y
- `sep #$30` = set 8-bit A and X/Y
- `php` / `plp` = push/pull processor status (CRITICAL for mode preservation)
- `phb` / `plb` = push/pull data bank register
- `phk` / `plb` = set data bank to program bank
- `mvn src,dst` = block move next (decrementing)
- `xba` = exchange B and A (swap high/low bytes of 16-bit accumulator)
- `tax` / `tay` = transfer accumulator to index — **DANGER**: with M=1/X=0, transfers full 16-bit C including hidden B byte. See [Mixed-Mode Transfers](reference/mixed-mode-transfers.md).
- `txa` / `tya` = transfer index to accumulator — with M=1/X=0, sets hidden B to index high byte
- `jsl` / `rtl` = long subroutine call/return (24-bit)
- `jsr` / `rts` = short subroutine call/return (16-bit, same bank)

## BGR555 Color Format

Each color is 2 bytes, little-endian: `low_byte, high_byte`
Bit layout: `0bbbbbgg_gggrrrrr` (15-bit, bit 15 unused)

| Example | Bytes | Color |
|---------|-------|-------|
| Black | `$00, $00` | R=0, G=0, B=0 |
| White | `$ff, $7f` | R=31, G=31, B=31 |
| Bright red | `$1f, $00` | R=31, G=0, B=0 |
| Bright green | `$e0, $03` | R=0, G=31, B=0 |
| Bright blue | `$00, $7c` | R=0, G=0, B=31 |
| Dark blue | `$00, $40` | R=0, G=0, B=16 |

Conversion: `low = (green_low3 << 5) | red5`, `high = (blue5 << 2) | green_high2`

## COLDATA Format ($2132)

`[bit7=B][bit6=G][bit5=R][bits4-0=intensity]`
- `$3f` = R=31, `$5f` = G=31, `$9f` = B=31
- `$e0` = all planes intensity 0, `$ff` = all planes intensity 31

## hiprint Text Rendering Pattern

```asm
; snescom syntax:
  lda #<row>          ; tile row (9+ = below logo)
  sta print_y
  lda #<col>          ; tile column (0 = left edge)
  sta print_x
  lda #^string_label  ; bank byte of string
  sta print_bank
  ldx #!string_label  ; 16-bit address of string
  stx print_src
  stz print_pal       ; palette 0=normal, 1=bold
  lda #<max_chars>
  sta print_count
  jsr hiprint
```

Strings: null-terminated ASCII. Chars 0 and 1 = end of string.
After hiprint, wait for NMI DMA: `- lda isr_done / lsr / bcc - / stz isr_done`

## NMI Handler Constraints

Fires every VBlank (~60Hz). DMAs BG1/BG2 tile buffers WRAM->VRAM, updates cursor bar, fades brightness (cur_bright toward tgt_bright), sets isr_done=1.

**CRITICAL**: Write to WRAM buffers via hiprint, NOT directly to VRAM. NMI overwrites VRAM every frame.

## WRAM Routine Safety

1. ALWAYS `php`/`plp` to save/restore processor state
2. When changing routine size, update DMA7 copy size in `store_wram_routines`
3. Do NOT add timeouts to WRAM routines on the real-hardware path

## Memory Map

| Address | Name | Purpose |
|---------|------|---------|
| `$002A00` | MCU_CMD | Command register (SNES->MCU) |
| `$002A02` | SNES_CMD | Status register (MCU->SNES) |
| `$7EA000` | BG2_TILE_BUF | BG2 tile buffer (NMI DMAs to VRAM) |
| `$7EB000` | BG1_TILE_BUF | BG1 tile buffer (NMI DMAs to VRAM) |
| `$7EF000` | WRAM_ROUTINE | FPGA reconfig routine |
| `$7EF200` | WRAM_WAIT_MCU | MCU wait routine |
| `$FF019D` | CFG_BRIGHTNESS_LIMIT | Screen brightness config |

## Detailed References

- [PPU Registers](reference/ppu-registers.md) — All PPU/CPU registers with bit layouts, initial values, BG mode summary (manual-validated)
- [OBJ/Sprites](reference/obj-sprites.md) — OAM format, size tables, priority rules, per-scanline limits, setup sequence, code examples
- [BG/Backgrounds](reference/bg-backgrounds.md) — BG modes, tilemap format, CGRAM layout, character data formats, priority ordering, setup sequence
- [Window Masking](reference/window-mask.md) — Window 1/2 registers, IN/OUT modes, mask logic (OR/AND/XOR/XNOR), color window, setup sequence
- [DMA & HDMA](reference/dma-hdma.md) — GPDMA bulk transfers, HDMA per-scanline effects, transfer modes, B-bus patterns, table format, channel allocation, V-Blank cycle budget, CGRAM/VRAM/OAM access windows
- [Hardware Math](reference/hardware-math.md) — Hardware multiply ($4202/$4203), divide ($4204-$4206), result registers ($4214-$4217), cycle wait times, signed multiply via Mode 7 regs, codebase examples
- [65816 Addressing Modes](reference/addressing-modes.md) — All addressing modes with snescom syntax
- [Mixed-Mode Transfers](reference/mixed-mode-transfers.md) — Hidden B register trap: TAX/TAY in mixed M=1/X=0 mode, safe patterns, audit checklist
