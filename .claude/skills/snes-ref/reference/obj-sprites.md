# SNES OBJ (Sprite) Reference

Source: Nintendo SNES Development Manual, Book I — Sections 2-2, 2-20, Appendix A (pp. A-3/A-4)

## Overview

- **128 OBJs** maximum on screen
- **4 bpp** (16 colors per sprite, from 8 palettes of 16 colors each)
- Palettes 0-7 from CGRAM colors 128-255 (palette N = CGRAM 128 + N*16)
- Two sizes selectable per frame via $2101; each OBJ chooses small or large
- Attributes: H/V flip, BG priority (0-3), palette select, character name (0-511)

## OAM Memory Layout

OAM is 544 bytes total: a 512-byte low table + a 32-byte high table.

### Low Table (512 bytes, OAM addresses 0-511)

4 bytes per OBJ, 128 OBJs:

| Byte | Bits | Content |
|------|------|---------|
| 0 | 7-0 | H-position (low 8 bits) |
| 1 | 7-0 | V-position (8 bits, 0-239 visible) |
| 2 | 7-0 | Character name (low 8 bits, bit 8 in byte 3) |
| 3 | 7 | V-flip |
| 3 | 6 | H-flip |
| 3 | 5-4 | Priority vs BG (0=lowest, 3=highest) |
| 3 | 3-1 | Palette number (0-7) |
| 3 | 0 | Character name bit 8 (selects Name Base vs Name+Select area) |

**Byte 3 bit layout**: `VHPPCCCn`
- V = V-flip, H = H-flip
- PP = Priority (00-11)
- CCC = Palette (000-111 = palette 0-7)
- n = Name bit 8 (0 = base area, 1 = base+select area)

### High Table (32 bytes, OAM addresses 512-543)

2 bits per OBJ, packed 4 OBJs per byte:

| Bits | Content |
|------|---------|
| bit 1 | Size select (0=small, 1=large) |
| bit 0 | H-position bit 8 (MSB, sign bit for 9-bit position) |

Byte N covers OBJs (N*4) through (N*4+3):
- Bits 1,0 = OBJ N*4
- Bits 3,2 = OBJ N*4+1
- Bits 5,4 = OBJ N*4+2
- Bits 7,6 = OBJ N*4+3

### OAM Address Mapping

```
OBJ 0:  Low table bytes 0-3,    High table byte 0 bits 1,0
OBJ 1:  Low table bytes 4-7,    High table byte 0 bits 3,2
OBJ 2:  Low table bytes 8-11,   High table byte 0 bits 5,4
OBJ 3:  Low table bytes 12-15,  High table byte 0 bits 7,6
OBJ 4:  Low table bytes 16-19,  High table byte 1 bits 1,0
...
OBJ 127: Low table bytes 508-511, High table byte 31 bits 7,6
```

## H-Position (9-bit signed)

The full H-position is 9 bits: `{high_table_bit0, low_table_byte0}`.

| 9-bit value | Decimal | Meaning |
|-------------|---------|---------|
| $000-$0FF | 0-255 | On-screen (left to right) |
| $100-$1FF | -256 to -1 | Off-screen left (2's complement) |

- **$100 is prohibited** as an H-position per Nintendo docs. If used, the OBJ still counts toward the per-line limit even though it's not displayed.
- To hide a sprite: set V-position to $F0+ (offscreen below visible area 0-223) or set H-position far off-screen.

## V-Position (8-bit, wrapping)

- 0-223: visible on NTSC (0-238 on PAL with overscan)
- 224-255: offscreen below (wraps to top on next frame)
- **$F0** (240) is the standard "hide sprite" Y value
- V-position is 1 pixel offset from BG coordinates (OBJ Y=0 aligns with BG scanline 1)

## OBJ Size Select ($2101 OBSEL)

Register $2101 selects which two sizes are available:

| S2 S1 S0 | Small | Large |
|-----------|-------|-------|
| 000 | 8x8 | 16x16 |
| 001 | 8x8 | 32x32 |
| 010 | 8x8 | 64x64 |
| 011 | 16x16 | 32x32 |
| 100 | 16x16 | 64x64 |
| 101 | 32x32 | 64x64 |

Each OBJ selects small or large via its high table size bit.

### $2101 Register Layout

```
D7  D6  D5  D4  D3  D2  D1  D0
S2  S1  S0  N1  N0  BA2 BA1 BA0
```

- **S2-S0**: Size select (table above)
- **N1-N0**: Name Select — determines which 4K-word block pairs with the base area for name bit 8 = 1
- **BA2-BA0**: Name Base Address — selects which 8K-word segment in VRAM holds OBJ tiles (BA2 is for expansion, normally 0)

### Name Base Address (BA)

VRAM is 32K words. BA selects 8K-word segments:

| BA1 BA0 | VRAM Word Address |
|---------|-------------------|
| 00 | $0000 |
| 01 | $2000 |
| 10 | $4000 |
| 11 | $6000 |

The upper 4K-words of the selected segment are the **base area** (name 0-255).
The **name select** (N1,N0) picks which other 4K-word block is combined with it for names 256-511.

### sd2snes Menu Example

```asm
lda #$03      ; S2S1S0=000 (8x8/16x16), N1N0=00, BA=011 ($6000)
sta $2101
```
This means: small=8x8, large=16x16, OBJ tiles at VRAM $6000.

## OBJ Character Data Format (4bpp)

OBJ tiles are always 4 bits per pixel (16 colors). Each 8x8 tile is 32 bytes (16 words):

```
Row 0: plane0_lo, plane1_lo   (bytes 0-1)
Row 1: plane0_lo, plane1_lo   (bytes 2-3)
...
Row 7: plane0_lo, plane1_lo   (bytes 14-15)
Row 0: plane2_lo, plane3_lo   (bytes 16-17)
Row 1: plane2_lo, plane3_lo   (bytes 18-19)
...
Row 7: plane2_lo, plane3_lo   (bytes 30-31)
```

For larger sprites (16x16, 32x32, 64x64), the character name refers to the top-left 8x8 tile. Adjacent tiles are arranged in VRAM as a 16-wide grid:

```
16x16 sprite with name N:
  N    N+1    (top row: 8x8 tiles side by side)
  N+16 N+17   (bottom row: 16 tiles later in VRAM)
```

```
32x32 sprite with name N:
  N    N+1  N+2  N+3
  N+16 N+17 N+18 N+19
  N+32 N+33 N+34 N+35
  N+48 N+49 N+50 N+51
```

## Per-Scanline Limits

### 32 OBJ Range Limit ("33's Range Over")

Maximum **32 OBJs** per horizontal scanline regardless of size. If 33+ OBJs fall on the same line, the lowest-numbered 32 are drawn and the rest are dropped. Register $213E bit 6 is set when this occurs.

**Note**: OBJs hidden behind BG or other OBJs still count. OBJs entirely off the left edge (negative H-position with no visible pixels) do NOT count.

### 34-tile Time Limit ("35's Time Over")

Maximum **34 character tiles** (8x8 equivalent) per horizontal scanline. A 16x16 sprite uses 2 tiles per line, a 32x32 uses 4, a 64x64 uses 8. If exceeded, tiles are dropped from the highest-numbered OBJs first. Register $213E bit 7 is set.

**Note**: Off-screen 8x8 sub-tiles of a large sprite that fall outside the display area do NOT count toward this limit.

### Flicker Mitigation: Priority Rotation

To prevent the same sprites from always being dropped, rotate OBJ priority each frame:

1. Set $2103 bit 7 = 1 (enable priority rotation)
2. Each V-Blank, write the highest-priority OBJ number (0-127) to $2102 bits 1-7
3. Increment this number each frame

This causes dropped sprites to alternate, producing flicker instead of permanent disappearance.

## OBJ Priority vs BG Layers

Each OBJ has a 2-bit priority field (0-3). How this interacts with BG depends on BG mode. The general rule for Mode 1 (most common):

```
Front                                    Back
OBJ pri3 > BG1 pri1 > BG2 pri1 > OBJ pri2 >
BG1 pri0 > BG2 pri0 > OBJ pri1 > BG3 pri1 >
OBJ pri0 > BG3 pri0 > Backdrop
```

When BG3 priority bit is set in $2105 (Mode 1):
```
BG3 pri1 > OBJ pri3 > BG1 pri1 > BG2 pri1 >
OBJ pri2 > BG1 pri0 > BG2 pri0 > OBJ pri1 >
OBJ pri0 > BG3 pri0 > Backdrop
```

For Mode 0: each BG has its own priority bit; OBJ priority 0-3 slots between them.

For Mode 3 (used by sd2snes menu):
```
OBJ pri3 > BG1 pri1 > OBJ pri2 > BG2 pri1 >
OBJ pri1 > BG1 pri0 > OBJ pri0 > BG2 pri0 > Backdrop
```

## Color Math with OBJs

OBJ color math (addition/subtraction) only applies to **palettes 4-7** (CGRAM colors 192-255). Palettes 0-3 are never affected by color math, making them useful for HUD elements that should not be tinted.

## Accessing OAM

OAM can only be written during **V-Blank** or **Forced Blank** ($2100 bit 7 = 1).

### Writing OAM via DMA

```asm
; Set OAM address to start of low table
ldx #$0000
stx $2102

; DMA the full low table (512 bytes) + high table (32 bytes) = 544 bytes
; Mode $00 = 1-byte transfer, B-bus $04 = OAMDATA
DMA7(#$00, #$0220, #^oam_buffer, #!oam_buffer, #$04)
```

### Writing Individual OAM Entries

```asm
; Write OBJ 5 (low table offset = 5*4 = 20 = $14/2 = word addr $0A)
ldx #$000A          ; word address for OBJ 5
stx $2102           ; set OAM address
lda #<x_pos>
sta $2104           ; byte 0: X position low
lda #<y_pos>
sta $2104           ; byte 1: Y position
lda #<char_name>
sta $2104           ; byte 2: character name low 8 bits
lda #<attr>         ; VHPPCCCn
sta $2104           ; byte 3: attributes
```

**Important**: After writing to $2102/$2103, the internal OAM address auto-reloads at the start of each V-Blank to the last value written during the previous V-Blank period. This does NOT happen during Forced Blank.

## sd2snes Menu OAM Usage

The menu uses OAM for the sd2snes logo sprites in `const.a65`:

### Low Table Data (`oam_data_l`)
24 sprites defined, each 4 bytes: `x, y, name, attr`
- OBJs 0-12: Logo character sprites at positions (88-136, 56-72), palette 0 (attr $08 = priority 1, palette 0)
- OBJs 13-22: Additional logo pieces using palettes 1-3

### High Table Data (`oam_data_h`)
9 bytes covering OBJs 0-35. All zeros = all sprites are small size, H-position bit 8 = 0.

### Setup in `main.a65` (`setup_gfx`)
```asm
; Clear all OAM (544 bytes of zeros)
ldx #$0000
stx $2102
DMA7(#$08, #$220, #^zero, #!zero, #$04)

; Load sprite tile data to VRAM at OAM_TILE_BASE ($6000)
ldx #OAM_TILE_BASE
stx $2116
DMA7(#$01, #$500, #^logospr, #!logospr, #$18)

; Load low table (96 bytes = 24 sprites * 4)
ldx #$0000
stx $2102
DMA7(#$00, #$60, #^oam_data_l, #!oam_data_l, #$04)

; Load high table (9 bytes)
ldx #$0100
stx $2102
DMA7(#$00, #$09, #^oam_data_h, #!oam_data_h, #$04)
```

### Hiding Unused Sprites

**Pitfall**: Clearing OAM to all zeros places 128 sprites at position (0,0) with tile 0 — they ARE visible if the OBJ layer is enabled! Two solutions:

1. **Disable OBJ layer**: Set $212C to $03 (BG1+BG2 only, no OBJ)
2. **Move sprites off-screen**: Set Y position to $F0 for all unused OBJs

The sd2snes menu clears OAM to zeros first, then writes only the sprites it needs. The unused sprites at (0,0) are visible as a small artifact unless the OBJ layer is masked or they're moved off-screen.

## Official OBJ Setup Sequence (from Manual Section 2.3)

Nintendo's prescribed order of operations for displaying OBJs, derived from the Setting Example flowchart:

### Phase 1: Initial Settings (any time)
```
1. Clear each register (snes_init)
2. Set $2101 (OBSEL):
   - OBJ Size Select (which two sizes)
   - OBJ Name Select (tile area pairing)
   - OBJ Name Base Address (VRAM segment)
3. Set $2133 D1: "OBJ V Select" (interlace mode for OBJ, normally 0)
4. Set $212C D4: "Through Main OBJ" (enable OBJ on main screen)
```

### Phase 2: Forced Blank (screen off, $2100 bit 7 = 1)
```
5. Set $2115: VRAM address increment mode
6. Set $2116-$2119: Load OBJ character tile data to VRAM via DMA
7. Set $2121/$2122: Load OBJ palette data to CGRAM via DMA
```

### Phase 3: V-Blank (every frame, or once during setup)
```
8. Set $2102-$2104: Write OAM data
   - OAM Address
   - OAM Priority Rotation (if using flicker mitigation)
   - OAM Data (transfer OBJ data to OAM by DMA)
9. Display (turn off forced blank: $2100 = $0F)
```

**CAUTION** (from manual): It is prohibited to write $100 to the OAM H-position (9-bit). See H-Position section above.

**Key insight**: Tile data and palette go to VRAM/CGRAM during Forced Blank, but OAM data should be written during V-Blank for proper auto-reload behavior. The sd2snes menu loads everything during Forced Blank at boot (which works fine for one-time setup).

## Quick Recipe: Display a Single Sprite

```asm
; During forced blank ($2100 = $8F):

; 1. Configure OBSEL: 8x8/16x16, tiles at VRAM $6000
  lda #$03          ; S=000, N=00, BA=011
  sta $2101

; 2. Load tile data to VRAM
  ldx #$6000
  stx $2116
  lda #$80          ; increment on high write
  sta $2115
  DMA7(#$01, #tile_size, #^tile_data, #!tile_data, #$18)

; 3. Set OAM for OBJ 0 (4 bytes at OAM word address $0000)
  ldx #$0000
  stx $2102
  lda #100          ; X = 100
  sta $2104
  lda #80           ; Y = 80
  sta $2104
  lda #$00          ; tile name = 0
  sta $2104
  lda #$08          ; V=0 H=0 PP=01 CCC=000 n=0
  sta $2104

; 4. Set high table for OBJ 0 (small size, H-pos bit 8 = 0)
  ldx #$0100
  stx $2102
  lda #$00
  sta $2104

; 5. Hide remaining sprites (set Y=$F0 for OBJ 1-127)
;    ... or disable OBJ in $212C

; 6. Enable OBJ layer on main screen
  lda #$13          ; BG1 + BG2 + OBJ
  sta $212C

; 7. Load sprite palette to CGRAM (palette 0 = colors 128-143)
  lda #$80          ; CGRAM address 128
  sta $2121
  DMA7(#$00, #$20, #^sprite_palette, #!sprite_palette, #$22)

; 8. Turn off forced blank
  lda #$0F
  sta $2100
```
