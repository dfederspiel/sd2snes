# SNES Background (BG) Reference

Source: Nintendo SNES Development Manual, Book I — Sections 2-3, 2-12 (Offset Change), Appendix A (pp. A-5 through A-22)

## Overview

- Up to **4 BG layers** (depending on mode)
- 8 BG modes (0-7), each with different layer counts, color depths, and features
- Per-tile attributes: palette, priority, H/V flip
- Scrollable independently per layer (H/V offset)
- Character (tile) sizes: 8x8 or 16x16 per layer
- Screen (tilemap) sizes: 32x32, 64x32, 32x64, or 64x64 tiles

## BG Mode Summary

| Mode | BG1 | BG2 | BG3 | BG4 | Resolution | Special Features |
|------|-----|-----|-----|-----|------------|-----------------|
| 0 | 4-color (2bpp) | 4-color | 4-color | 4-color | 256x224 | 4 layers, 32 colors each |
| 1 | 16-color (4bpp) | 16-color | 4-color (2bpp) | — | 256x224 | Most common game mode |
| 2 | 16-color | 16-color | — | — | 256x224 | Offset-per-tile (column scroll) |
| 3 | 256-color (8bpp) | 16-color | — | — | 256x224 | Direct color option |
| 4 | 256-color | 4-color | — | — | 256x224 | Offset-per-tile + direct color |
| 5 | 16-color | 4-color | — | — | 512x224 | Hires (pseudo-512px) |
| 6 | 16-color | — | — | — | 512x224 | Hires + offset-per-tile |
| 7 | 256-color | (128-color EXTBG) | — | — | 256x224 | Rotation/scaling/zoom |

### Color Depth → Tile Size in VRAM

| Depth | Colors | Bits/pixel | Bytes per 8x8 tile | VRAM words per tile |
|-------|--------|------------|---------------------|---------------------|
| 2bpp | 4 | 2 | 16 bytes | 8 words |
| 4bpp | 16 | 4 | 32 bytes | 16 words |
| 8bpp | 256 | 8 | 64 bytes | 32 words |

## CGRAM Palette Layout by Mode

Palettes are stored in CGRAM (256 entries, 512 bytes). Layout depends on BG mode:

### Mode 0 (4 layers, each 4-color x 8 palettes)
```
$00-$1F: BG1 palettes 0-7 (4 colors each, 32 entries)
$20-$3F: BG2 palettes 0-7
$40-$5F: BG3 palettes 0-7
$60-$7F: BG4 palettes 0-7
$80-$FF: OBJ palettes 0-7 (16 colors each, 128 entries)
```

### Mode 1, 2 (BG1/BG2 = 16-color, BG3 = 4-color)
```
$00-$7F: BG1 & BG2 palettes (16-color x 8 palettes, shared)
$80-$FF: OBJ palettes 0-7
```
BG3 (Mode 1) uses entries $00-$1F (4-color x 8 palettes overlapping with BG1/BG2).

### Mode 3, 4, 7 (BG1 = 256-color)
```
$00-$FF: BG1 uses all 256 entries (single palette)
$80-$FF: OBJ palettes (shared with BG1 upper half!)
```
BG2 in Mode 3: $00-$7F (16-color x 8 palettes, shared with BG1).
BG2 in Mode 4: $00-$1F (4-color x 8 palettes, shared with BG1).

### Mode 5, 6 (hires)
```
$00-$1F: BG2 palettes (4-color x 8, Mode 5 only)
$00-$7F: BG1 palettes (16-color x 8)
$80-$FF: OBJ palettes 0-7
```

**Key rule**: Color 0 of every palette is always transparent. The backdrop color is CGRAM entry $00.

## BG SC (Tilemap) Data Format (Modes 0-6)

Each tilemap entry is 16 bits (1 word):

```
D15  D14  D13  D12  D11  D10  D9  D8  D7-D0
 V    H   Pri  Pal2 Pal1 Pal0  Name (10-bit, 0-1023)
```

| Bits | Content |
|------|---------|
| 15 | V-flip |
| 14 | H-flip |
| 13 | Priority (0 or 1, per-tile BG priority) |
| 12-10 | Palette number (0-7) |
| 9-0 | Character name (0-1023, indexes into character data in VRAM) |

### Mode 7 Tilemap Data

Mode 7 is different: tilemap and character data are interleaved in VRAM.
- Even bytes: 8-bit character name (0-255)
- Odd bytes: 8-bit pixel data for that character
- 128x128 tile grid, each tile 8x8, 256 colors

## Screen (Tilemap) Size

Set by D1-D0 of $2107-$210A:

| S1 S0 | Layout | Pixel Size (8x8 tiles) | Pixel Size (16x16 tiles) |
|-------|--------|------------------------|--------------------------|
| 00 | 32x32 (1 screen) | 256x256 | 512x512 |
| 01 | 64x32 (2 horizontal) | 512x256 | 1024x512 |
| 10 | 32x64 (2 vertical) | 256x512 | 512x1024 |
| 11 | 64x64 (4 screens) | 512x512 | 1024x1024 |

### Tilemap Memory Layout

Each 32x32 tile screen = 2KB (1K words). For multi-screen layouts:

```
SC Size 00 (32x32):     SC Size 01 (64x32):
  +------+                +------+------+
  | SC0  |                | SC0  | SC1  |
  +------+                +------+------+

SC Size 10 (32x64):     SC Size 11 (64x64):
  +------+                +------+------+
  | SC0  |                | SC0  | SC1  |
  +------+                +------+------+
  | SC1  |                | SC2  | SC3  |
  +------+                +------+------+
```

VRAM addresses: SC0 at base, SC1 at base+$400, SC2 at base+$800, SC3 at base+$C00.

## BG Character Data Address

Set by $210B/$210C. Each 4-bit nibble selects a 4K-word (8KB) segment:

| Value | VRAM Word Address |
|-------|-------------------|
| 0 | $0000 |
| 1 | $1000 |
| 2 | $2000 |
| 3 | $3000 |
| 4 | $4000 |
| ... | ... |
| 7 | $7000 |

$210B: BG1 (D3-D0), BG2 (D7-D4)
$210C: BG3 (D3-D0), BG4 (D7-D4)

## BG Scroll Registers

Write-twice registers (low byte then high byte):

| Register | Layer | Range |
|----------|-------|-------|
| $210D | BG1 H-scroll | 0-1023 (10-bit), Mode 7: -4096 to 4095 (13-bit signed) |
| $210E | BG1 V-scroll | 0-1023 |
| $210F | BG2 H-scroll | 0-1023 |
| $2110 | BG2 V-scroll | 0-1023 |
| $2111 | BG3 H-scroll | 0-1023 |
| $2112 | BG3 V-scroll | 0-1023 |
| $2113 | BG4 H-scroll | 0-1023 |
| $2114 | BG4 V-scroll | 0-1023 |

**Note**: Adding 1 to H-scroll scrolls left. Adding 1 to V-scroll scrolls up.

**Note**: With 16x16 character size, scroll range doubles (0-2047 effective).

**Note**: BG and OBJ V-coordinates have a 1-line gap. OBJ Y=0 aligns with BG scanline 1.

## BG & OBJ Priority Order

### Modes 0 and 1 (3-4 screen mode)

```
Front ◄─────────────────────────────────────────► Back

BG3p1* > OBJ p3 > BG1p1 > BG2p1 > OBJ p2 >
BG1p0 > BG2p0 > OBJ p1 > BG3p1 > BG4p1 >
OBJ p0 > BG3p0 > BG4p0 > Backdrop
```
*BG3p1 is front-most only when $2105 D3=1 (BG3 priority mode).

Without BG3 priority bit ($2105 D3=0):
```
OBJ p3 > BG1p1 > BG2p1 > OBJ p2 > BG1p0 > BG2p0 >
OBJ p1 > BG3p1 > BG4p1 > OBJ p0 > BG3p0 > BG4p0 > Backdrop
```

### Modes 2-7 (1-2 screen mode)

```
Front ◄────────────────────────────────► Back

OBJ p3 > BG1p1 > OBJ p2 > BG2p1 >
OBJ p1 > BG1p0 > OBJ p0 > BG2p0 > Backdrop
```

Where `pN` = priority bit N in the tilemap entry (BG) or OAM attribute (OBJ).

**Among OBJs**: Lower-numbered OBJ has higher priority (OBJ 0 is frontmost), unless priority rotation is enabled via $2103.

## Official BG Setup Sequence (from Manual Section 3.3)

Nintendo's prescribed order of operations for displaying BG layers:

### Phase 1: Initial Settings (any time)
```
1. Clear each register (snes_init)
2. Set $2105 (BGMODE):
   - BG Mode (0-7)
   - BG Character Size (8x8 or 16x16 per layer)
3. Set $2107-$210A (BG1SC-BG4SC):
   - SC Size (tilemap dimensions)
   - SC Base Address (VRAM segment for tilemap)
4. Set $210B/$210C (BG12NBA/BG34NBA):
   - Character Name Base Address (VRAM segment for tile data)
5. Set $212C D0-D3: "Through Main BG" (enable BG layers on main screen)
```

### Phase 2: Forced Blank (screen off, $2100 bit 7 = 1)
```
6. Set $2115: VRAM address increment mode (H/L INC)
7. Set $2116-$2119: Load BG-SC data AND BG character data to VRAM via DMA
8. Set $2121/$2122: Load BG color data to CGRAM via DMA
```

### Phase 3: V-Blank (every frame for scrolling)
```
9. Set $210D-$2114: BG H/V Offset (scroll positions)
```

**Note**: In BG Mode 5 or 6, also set $212D (Through Sub BG) — hires modes require both main and sub screen designation.

## sd2snes Menu BG Configuration

From `video_init` in `main.a65`:

```asm
video_init:
  sep #$20 : .as
  rep #$10 : .xl

  ; BG Mode 3 (256-color BG1 + 16-color BG2)
  ; Mode 5 is enabled per-scanline via HDMA channel 0
  lda #$03
  sta $2105         ; BGMODE = Mode 3

  ; BG1 tilemap at VRAM $5800 (word addr), SC size 32x64
  lda #$58
  ora #$02          ; SC size = 10 (32x64)
  sta $2107         ; BG1SC = $5A

  ; BG2 tilemap at VRAM $5000, SC size 32x64
  lda #$50
  ora #$02
  sta $2108         ; BG2SC = $52

  ; Character base: BG1 at $0000, BG2 at $8000
  lda #$40
  sta $210b         ; BG12NBA: BG1=0, BG2=4 (4*$1000=$4000 word = $8000 byte)

  ; Enable BG1 + BG2 + OBJ on both main and sub screen
  lda #$13          ; bits: 0=BG1, 1=BG2, 4=OBJ
  sta $212c         ; TM (main screen)
  sta $212d         ; TS (sub screen) — needed for Mode 5 hires text
```

### VRAM Layout (sd2snes menu)

```
$0000-$1FFF: BG1 character data (logo tiles, 4bpp)
$2000-$3FFF: (logo tile data continued)
$4000-$5FFF: BG2 character data (font tiles)
$5000-$57FF: BG2 tilemap (32x64)
$5800-$5FFF: BG1 tilemap (32x64)
$6000-$62FF: OBJ character data (sprite tiles)
```

## Character Data Formats

### 2bpp (4 colors, used by Mode 0 all layers, Mode 1 BG3, Mode 5 BG2)

Each 8x8 tile = 16 bytes:
```
Row 0: plane0, plane1   (2 bytes)
Row 1: plane0, plane1
...
Row 7: plane0, plane1
```
Total: 16 bytes per tile, 8 words.

### 4bpp (16 colors, used by Mode 1 BG1/BG2, Mode 3 BG2, Mode 5 BG1)

Each 8x8 tile = 32 bytes:
```
Row 0: plane0, plane1   (bytes 0-1)
Row 1: plane0, plane1   (bytes 2-3)
...
Row 7: plane0, plane1   (bytes 14-15)
Row 0: plane2, plane3   (bytes 16-17)
...
Row 7: plane2, plane3   (bytes 30-31)
```
Total: 32 bytes per tile, 16 words. Same format as OBJ tiles.

### 8bpp (256 colors, used by Mode 3/4 BG1, Mode 7)

Each 8x8 tile = 64 bytes:
```
Planes 0-1: rows 0-7 (16 bytes)
Planes 2-3: rows 0-7 (16 bytes)
Planes 4-5: rows 0-7 (16 bytes)
Planes 6-7: rows 0-7 (16 bytes)
```
Total: 64 bytes per tile, 32 words.

### Mode 7 (special interleaved format)

Character data and tilemap share VRAM:
- Even addresses: tilemap entries (8-bit character name)
- Odd addresses: 8-bit pixel data per character row

## Quick Recipe: Display a BG Layer

```asm
; During forced blank ($2100 = $8F):

; 1. Set BG Mode 1, 8x8 characters
  lda #$01
  sta $2105

; 2. Set BG1 tilemap at VRAM $5800, 32x32 screen
  lda #$58          ; base address bits
  ora #$00          ; SC size 00 = 32x32
  sta $2107

; 3. Set BG1 character data at VRAM $0000
  lda #$00          ; BG1=0, BG2=0
  sta $210b

; 4. Load character (tile) data to VRAM via DMA
  lda #$80
  sta $2115         ; increment on high write
  ldx #$0000
  stx $2116         ; VRAM address $0000
  DMA7(#$01, #tile_data_size, #^tile_data, #!tile_data, #$18)

; 5. Load tilemap to VRAM
  ldx #$5800        ; tilemap VRAM address
  stx $2116
  DMA7(#$01, #$0800, #^tilemap_data, #!tilemap_data, #$18)

; 6. Load palette to CGRAM
  stz $2121         ; CGRAM address 0
  DMA7(#$00, #$20, #^palette_data, #!palette_data, #$22)

; 7. Enable BG1 on main screen
  lda #$01
  sta $212c

; 8. Set scroll position (0,0)
  stz $210d         ; BG1 H-scroll low
  stz $210d         ; BG1 H-scroll high
  stz $210e         ; BG1 V-scroll low
  stz $210e         ; BG1 V-scroll high

; 9. Turn off forced blank
  lda #$0f
  sta $2100
```

## Offset-Per-Tile (Modes 2, 4, 6)

In these modes, BG3's tilemap data is repurposed as column-by-column scroll offsets for BG1 and BG2. This allows each 8-pixel column to have a different H/V scroll value — enabling effects like wavy water, parallax strips, or per-column distortion.

BG3 SC data provides offset values:
- Mode 2/6: H-offset only (per column)
- Mode 4: H-offset or V-offset selectable per column (D15 of offset data)

The first column (column 0) cannot have its offset changed — it always uses the global BG scroll value.

## Common Pitfalls

- **VRAM write timing**: Tilemap and character data can only be written during Forced Blank or V-Blank. Writing during active display corrupts data.
- **Scroll registers are write-twice**: Must write low byte then high byte. Writing only once leaves stale data in the latch.
- **Mode 5/6 require sub screen**: Hires modes combine main + sub screen. Must set $212D (TS) as well as $212C (TM).
- **BG character base granularity**: $210B/$210C select 4K-word (8KB) boundaries. Plan VRAM layout carefully to avoid overlap with tilemaps.
- **Mode 7 VRAM sharing**: Tilemap and character data are interleaved, consuming all 64KB of VRAM. No room for other BG layers or separate tile storage.
- **Color 0 transparency**: In every palette, color 0 is transparent (shows layer behind). The visible background color comes from CGRAM $00 (backdrop).
