# SNES PPU Register Reference

Source-validated against Nintendo SNES Development Manual, Book I — Chapter 27, Chapter 26 (Initial Settings), Appendix A.

## Display Control
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $2100 | INIDISP | Brightness (bits 0-3, 16 steps) and force blank (bit 7). $8F=blank, $0F=full | $8F |
| $2101 | OBSEL | OBJ size select (D7-D5), name select (D4-D3), name base addr (D2-D0) | $00 |
| $2105 | BGMODE | BG mode 0-7 (D2-D0), BG3 priority (D3), BG character size (D7-D4) | $00 |
| $2106 | MOSAIC | Mosaic size (D7-D4, 1-16 pixels), BG enable (D3-D0) | $00 |

### $2101 OBSEL Detail
```
D7  D6  D5  D4  D3  D2  D1  D0
S2  S1  S0  N1  N0  BA2 BA1 BA0
```
- **S2-S0**: Size select (see OBJ reference)
- **N1-N0**: Name Select (4K-word offset for name bit 8)
- **BA2-BA0**: Name Base Address (8K-word segment, BA2 normally 0)

### $2105 BGMODE Detail
```
D7    D6    D5    D4    D3       D2  D1  D0
BG4sz BG3sz BG2sz BG1sz BG3prio  Mode2-0
```
- Size bits: 0=8x8, 1=16x16 characters per BG layer
- BG3 priority: makes BG3 highest priority in Mode 0/1

## BG Tilemap / Character
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $2107-$210A | BG1SC-BG4SC | Tilemap base addr (D7-D2, 1K-word segments) and SC size (D1-D0) | $00 |
| $210B | BG12NBA | BG1 char base (D3-D0) / BG2 char base (D7-D4), 4K-word segments | $00 |
| $210C | BG34NBA | BG3 char base (D3-D0) / BG4 char base (D7-D4) | $00 |

### SC Size (D1-D0 of $2107-$210A)
| S1 S0 | Tilemap Size |
|-------|-------------|
| 00 | 32x32 (1 screen) |
| 01 | 64x32 (2 screens horizontal) |
| 10 | 32x64 (2 screens vertical) |
| 11 | 64x64 (4 screens) |

## BG Scroll (write-twice registers: low then high byte)
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $210D/$210E | BG1HOFS/VOFS | BG1 horizontal/vertical scroll (10-bit, 0-1023) | $00 $00 |
| $210F/$2110 | BG2HOFS/VOFS | BG2 scroll | $00 $00 |
| $2111/$2112 | BG3HOFS/VOFS | BG3 scroll | $00 $00 |
| $2113/$2114 | BG4HOFS/VOFS | BG4 scroll | $00 $00 |

**Note**: Mode 7 BG1 scroll is 13-bit signed (-4096 to 4095). All others are 10-bit (0-1023).

## Mode 7 Rotation/Scaling
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $211A | M7SEL | Mode 7 settings: screen flip H/V (D0-D1), screen over (D6-D7) | $00 |
| $211B | M7A | Mode 7 matrix parameter A (cosine, write-twice: low/high) | $00 $01 |
| $211C | M7B | Mode 7 matrix parameter B (sine, write-twice) | $00 $00 |
| $211D | M7C | Mode 7 matrix parameter C (-sine, write-twice) | $00 $00 |
| $211E | M7D | Mode 7 matrix parameter D (cosine, write-twice) | $00 $01 |
| $211F | M7X | Mode 7 center X (write-twice, 13-bit signed) | $00 $00 |
| $2120 | M7Y | Mode 7 center Y (write-twice, 13-bit signed) | $00 $00 |

### M7SEL ($211A) Detail
```
D7  D6  D5-D2  D1    D0
O1  O0  unused Vflip Hflip
```
- O1O0=00: wrap, O1O0=10: transparent, O1O0=11: tile 0 fill

## VRAM Access
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $2115 | VMAIN | Increment mode: D7=H/L select, D3-D2=full graphic, D1-D0=step | $80 |
| $2116/$2117 | VMADDL/H | VRAM word address (16-bit) | $00 |
| $2118/$2119 | VMDATAL/H | VRAM data write (low/high) | — |

### $2115 VMAIN Detail
```
D7    D6-D4  D3  D2    D1  D0
H/L   unused G1  G0    I1  I0
```
- **H/L**: 0=increment after $2118 write, 1=increment after $2119 write
- **I1I0**: 00=+1, 01=+32, 10=+128, 11=+128
- **G1G0**: Full graphic mode (remap address bits for bitplane-interleaved access)

## CGRAM (Palette)
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $2121 | CGADD | CGRAM word address (color index 0-255) | $00 |
| $2122 | CGDATA | CGRAM data (write BGR555 low then high byte) | — |

## OAM (Sprites)
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $2102/$2103 | OAMADDL/H | OAM word address. $2103 D7=priority rotation enable | $00 |
| $2104 | OAMDATA | OAM data write (write low then high byte, auto-increment) | — |

**Critical**: OAM address auto-reloads to last-set value at start of each V-Blank. Does NOT auto-reload during Forced Blank. Write only during V-Blank or Forced Blank.

See [obj-sprites.md](obj-sprites.md) for full OAM format and usage details.

## Screen Designation
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $212C | TM | Main screen layer enable (D4=OBJ, D3-D0=BG4-BG1) | $00 |
| $212D | TS | Sub screen layer enable (same bit layout) | $00 |

## Window Mask
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $2123 | W12SEL | Window 1/2 mask settings for BG1/BG2 | $00 |
| $2124 | W34SEL | Window 1/2 mask settings for BG3/BG4 | $00 |
| $2125 | WOBJSEL | Window 1/2 mask settings for OBJ and Color math | $00 |
| $2126 | WH0 | Window 1 left position | $00 |
| $2127 | WH1 | Window 1 right position | $00 |
| $2128 | WH2 | Window 2 left position | $00 |
| $2129 | WH3 | Window 2 right position | $00 |
| $212A | WBGLOG | Window mask logic for BG1-BG4 (OR/AND/XOR/NXOR per BG) | $00 |
| $212B | WOBJLOG | Window mask logic for OBJ and Color math | $00 |
| $212E | TMW | Window mask designation for main screen | $00 |
| $212F | TSW | Window mask designation for sub screen | $00 |

**Tip**: To disable a window, set left > right (e.g., $2126=1, $2127=0).

## Color Math
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $2130 | CGWSEL | Color math clip/prevent (D7-D6, D5-D4), direct color (D0) | $30 |
| $2131 | CGADSUB | Add/Sub select (D7), half (D6), layer enable (D5-D0) | $00 |
| $2132 | COLDATA | Fixed color: D7=B, D6=G, D5=R plane select, D4-D0=intensity | $E0 |

### $2130 CGWSEL Detail
```
D7  D6    D5  D4      D3-D2  D1    D0
Clip main  Prevent sub  unused  unused  Direct
```
- Clip: 00=never, 01=outside window, 10=inside window, 11=always
- Prevent: 00=never, 01=outside window, 10=inside window, 11=always

### $2131 CGADSUB Detail
```
D7     D6    D5   D4   D3   D2   D1   D0
Add/Sub Half  Back OBJ  BG4  BG3  BG2  BG1
```
- D7: 0=add, 1=subtract
- D6: 0=full result, 1=half result (average)
- D5-D0: which layers participate in color math

**OBJ color math restriction**: Only OBJ palettes 4-7 participate in color math. Palettes 0-3 are never affected.

### $2132 COLDATA Format
```
D7    D6    D5    D4-D0
Blue  Green Red   Intensity (0-31)
```
Multiple writes select which color planes to set. E.g.: `$3F`=R=31, `$5F`=G=31, `$9F`=B=31, `$E0`=all planes=0.

## Misc Display
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $2133 | SETINI | Interlace (D0), OBJ interlace (D1), overscan (D2), pseudo-hires (D3), EXTBG (D6) | $00 |

## Status Registers (Read-only)
| Register | Name | Purpose |
|----------|------|---------|
| $213E | STAT77 | PPU1 status: D7=time over (35's), D6=range over (33's), D5-D0=PPU1 version |
| $213F | STAT78 | PPU2 status: D7=interlace field, D6=ext latch, D5-D4=region, D3-D0=PPU2 version |

## CPU Registers (Interrupts / Joypad / Math)
| Register | Name | Purpose | Initial |
|----------|------|---------|---------|
| $4200 | NMITIMEN | NMI/IRQ enable. $81=NMI+auto joypad, $00=disabled | $00 |
| $4201 | WRIO | Programmable I/O port (active-low outputs) | $FF |
| $4202/$4203 | WRMPYA/B | Unsigned 8-bit multiply (A*B, result in $4216/$4217) | $00 |
| $4204-$4206 | WRDIVL/H/B | Unsigned division (16-bit/8-bit, result+remainder in $4214-$4217) | $00 |
| $4207-$420A | HTIMEL/H, VTIMEL/H | H/V IRQ trigger position | $00 |
| $420B | MDMAEN | DMA channel enable (1 bit per channel, write-triggered) | $00 |
| $420C | HDMAEN | HDMA channel enable (1 bit per channel) | $00 |
| $420D | MEMSEL | ROM access speed: 0=2.68MHz (slow), 1=3.58MHz (fast) | $00 |

## DMA Channel Registers ($43x0-$43xA, x=channel 0-7)
| Offset | Name | Purpose |
|--------|------|---------|
| $43x0 | DMAPx | Transfer mode (D2-D0), direction (D7: 0=A→B, 1=B→A), HDMA addressing (D6) |
| $43x1 | BBADx | B-bus address (PPU register low byte, e.g. $18 for VMDATAL) |
| $43x2-$43x4 | A1TxL/H/B | A-bus address (24-bit source/dest) |
| $43x5/$43x6 | DASxL/H | Byte count (GPDMA) or indirect table address (HDMA) |
| $43x7 | DASBx | Indirect HDMA bank byte |
| $43x8/$43x9 | A2AxL/H | HDMA table current address (internal) |
| $43xA | NTRLx | HDMA line counter (internal) |

### DMA Transfer Modes (D2-D0 of $43x0)
| Mode | Pattern | Bytes/cycle | Common use |
|------|---------|-------------|------------|
| 0 | 1 byte → 1 reg | 1 | CGDATA ($22), OAMDATA ($04) |
| 1 | 2 bytes → reg, reg+1 | 2 | VMDATAL+H ($18/$19) |
| 2 | 2 bytes → reg, reg | 2 | (uncommon) |
| 3 | 4 bytes → reg, reg, reg+1, reg+1 | 4 | (uncommon) |
| 4 | 4 bytes → reg, reg+1, reg+2, reg+3 | 4 | (uncommon) |
| 5 | 2 bytes → reg, reg+1 (repeat) | 4 | (uncommon) |

**Note**: DMA always runs at 2.68MHz regardless of MEMSEL setting.

## HDMA Table Format
Each entry: `count_byte, data_bytes...` terminated by `$00`.
- Bit 7 clear: **repeat** mode — same data for `count` scanlines
- Bit 7 set: **continuous** mode — `count & 0x7F` scanlines, new data bytes each line

Number of data bytes per entry depends on the transfer mode set in $43x0.

## Initial Register Settings (from Manual Chapter 26)

On power-on, registers are NOT guaranteed to be in any particular state. The recommended initialization sequence writes:
- $2100 = $8F (forced blank)
- All PPU registers $2101-$2133 = $00 (except $2115=$80, $2130=$30, $2132=$E0)
- All CPU registers $4200-$420D = $00 (except $4201=$FF)

**Critical**: This is why `snes_init` in `main.a65` writes zero to every register — the manual explicitly states register state is unstable at power-on.

## BG Mode Summary (from Manual Appendix A-5)

| Mode | BG1 | BG2 | BG3 | BG4 | Max Colors/Screen |
|------|-----|-----|-----|-----|-------------------|
| 0 | 4-color | 4-color | 4-color | 4-color | 32 per BG |
| 1 | 16-color | 16-color | 4-color | — | 128 per BG1/2 |
| 2 | 16-color | 16-color | — | — | 128, offset-per-tile |
| 3 | 256-color | 16-color | — | — | 256 BG1, 128 BG2 |
| 4 | 256-color | 4-color | — | — | 256 BG1, offset-per-tile |
| 5 | 16-color | 4-color | — | — | hires 512px |
| 6 | 16-color | — | — | — | hires 512px, offset-per-tile |
| 7 | 256-color | (EXTBG:128) | — | — | rotation/scaling |
