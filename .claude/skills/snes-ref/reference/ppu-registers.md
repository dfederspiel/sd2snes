# SNES PPU Register Reference

## Display Control
| Register | Name | Purpose |
|----------|------|---------|
| $2100 | INIDISP | Brightness (bits 0-3) and force blank (bit 7). $8F=blank, $0F=full |
| $2101 | OBSEL | OBJ size and base address |
| $2105 | BGMODE | BG mode (0-7) and tile size bits |
| $2106 | MOSAIC | Mosaic effect size and enable |

## BG Tilemap / Character
| Register | Name | Purpose |
|----------|------|---------|
| $2107-$210A | BG1SC-BG4SC | Tilemap address (bits 2-6) and size (bits 0-1) |
| $210B | BG12NBA | BG1 (bits 0-3) / BG2 (bits 4-7) character base |
| $210C | BG34NBA | BG3 (bits 0-3) / BG4 (bits 4-7) character base |

## BG Scroll (write twice: low then high byte)
| Register | Name | Purpose |
|----------|------|---------|
| $210D/$210E | BG1HOFS/VOFS | BG1 horizontal/vertical scroll |
| $210F/$2110 | BG2HOFS/VOFS | BG2 scroll |
| $2111/$2112 | BG3HOFS/VOFS | BG3 scroll |
| $2113/$2114 | BG4HOFS/VOFS | BG4 scroll |

## VRAM Access
| Register | Name | Purpose |
|----------|------|---------|
| $2115 | VMAIN | Increment mode (bit 7: 0=low, 1=high) and step |
| $2116/$2117 | VMADDL/H | VRAM word address |
| $2118/$2119 | VMDATAL/H | VRAM data write (low/high) |

## CGRAM (Palette)
| Register | Name | Purpose |
|----------|------|---------|
| $2121 | CGADD | CGRAM address (color index 0-255) |
| $2122 | CGDATA | CGRAM data (write BGR555 low then high byte) |

## OAM (Sprites)
| Register | Name | Purpose |
|----------|------|---------|
| $2102/$2103 | OAMADDL/H | OAM address |
| $2104 | OAMDATA | OAM data write |

## Screen Designation
| Register | Name | Purpose |
|----------|------|---------|
| $212C | TM | Main screen layer enable (bits: 0-3=BG1-4, 4=OBJ) |
| $212D | TS | Sub screen layer enable |

## Window / Color Math
| Register | Name | Purpose |
|----------|------|---------|
| $2123-$2125 | W12SEL/W34SEL/WOBJSEL | Window mask settings per layer |
| $2126-$2129 | WH0-WH3 | Window 1/2 left/right positions |
| $212E/$212F | TMW/TSW | Window mask for main/sub screen |
| $2130 | CGWSEL | Color math select (clip, prevent, source) |
| $2131 | CGADSUB | Color math designation (add/sub, half, layer enable) |
| $2132 | COLDATA | Fixed color data (COLDATA format) |

## Interrupts / DMA
| Register | Name | Purpose |
|----------|------|---------|
| $4200 | NMITIMEN | NMI/IRQ enable. $81 = NMI + auto joypad |
| $4207-$420A | HTIMEL/H, VTIMEL/H | IRQ trigger position |
| $420B | MDMAEN | DMA channel enable (1 bit per channel) |
| $420C | HDMAEN | HDMA channel enable (1 bit per channel) |

## DMA Channel Registers ($43x0-$43xA, x=channel 0-7)
| Offset | Name | Purpose |
|--------|------|---------|
| $43x0 | DMAPx | Transfer mode and direction |
| $43x1 | BBADx | B-bus address (PPU register, low byte only) |
| $43x2-$43x4 | A1TxL/H/B | A-bus address (24-bit source/dest) |
| $43x5/$43x6 | DASxL/H | Byte count (DMA) or indirect address (HDMA) |
| $43x7 | DASBx | Indirect HDMA bank |
| $43x8/$43x9 | A2AxL/H | HDMA table current address |
| $43xA | NTRLx | HDMA line counter |

## HDMA Table Format
Each entry: `count_byte, data_bytes...` terminated by `$00`.
- Bit 7 clear: repeat same data for `count` scanlines
- Bit 7 set: `count & 0x7F` scanlines, new data each line (continuous mode)

## BG Modes in Menu ROM
- Mode 3: Default (set in video_init)
- Mode 5: Hi-res text (pseudo-8x8 via two BG layers)
- HDMA channel 0 switches modes per scanline region
