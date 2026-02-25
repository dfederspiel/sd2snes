---
name: snes-ref
description: 65816 assembly and SNES PPU reference for the sd2snes menu ROM. Auto-loads when editing .a65 assembly files, working with SNES graphics, palettes, HDMA, or the menu ROM codebase.
user-invocable: false
---

# sd2snes Menu ROM - Quick Reference

## snescom Assembler Syntax

| Syntax | Meaning |
|--------|---------|
| `@label` or `@$addr` | Long (24-bit) address |
| `!label` or `!$addr` | Absolute (16-bit) address |
| `#^label` | Bank byte of label address |
| `#!label` | 16-bit address of label |
| `.as` / `.al` | 8-bit / 16-bit accumulator mode hint |
| `.xs` / `.xl` | 8-bit / 16-bit index register mode hint |
| `sep #$20 : .as` | Set 8-bit A (instruction + mode hint) |
| `rep #$10 : .xl` | Set 16-bit X/Y |
| `rep #$30 : .al : .xl` | Set 16-bit A and X/Y |
| `.byt` | Define byte(s) |
| `.word` | Define 16-bit word(s) |
| `- bra -` | Branch to previous anonymous label (infinite loop) |
| `-` / `+` | Anonymous labels (backward / forward) |

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

For full PPU register reference, see [reference/ppu-registers.md](reference/ppu-registers.md).
For 65816 addressing modes, see [reference/addressing-modes.md](reference/addressing-modes.md).
