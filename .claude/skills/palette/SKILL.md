---
name: palette
description: Design BGR555 color palettes for the SNES menu ROM. Use when discussing colors, gradients, themes, or editing palette.a65 or HDMA gradient tables in const.a65.
argument-hint: "[color-spec or theme-name]"
---

# SNES Palette Design Tool

Help design BGR555 color palettes for the sd2snes menu ROM.

## BGR555 Conversion

Each color: 2 bytes little-endian. Bit layout: `0bbbbbgg_gggrrrrr` (15-bit)

### RGB to BGR555:
1. Scale 0-255 to 0-31: `ch5 = round(ch8 / 255 * 31)`
2. Pack: `bgr555 = (blue5 << 10) | (green5 << 5) | red5`
3. Split: `low = bgr555 & 0xFF`, `high = (bgr555 >> 8) & 0xFF`
4. Output: `.byt $XX, $YY` (low first)

### Quick reference:
| RGB Hex | BGR555 bytes | R,G,B (5-bit) |
|---------|-------------|----------------|
| #000000 | `$00, $00` | 0, 0, 0 |
| #FFFFFF | `$FF, $7F` | 31, 31, 31 |
| #FF0000 | `$1F, $00` | 31, 0, 0 |
| #00FF00 | `$E0, $03` | 0, 31, 0 |
| #0000FF | `$00, $7C` | 0, 0, 31 |
| #FF00FF | `$1F, $7C` | 31, 0, 31 |
| #FFFF00 | `$FF, $03` | 31, 31, 0 |
| #00FFFF | `$E0, $7F` | 0, 31, 31 |

## Palette File: `snes/palette.a65`

512 bytes = 256 colors, 2 bytes each in BGR555.
- Color 0 palette 0 = background (overridden by HDMA gradient)
- Palette 0 = normal text colors
- Palette 1 = bold/highlight text (print_pal = 1)
- Palettes 2-7 = logo and sprite palettes

## HDMA Gradient: `snes/const.a65` label `hdma_pal_src`

Format: `scanline_count, low_byte, high_byte` repeated, `$00` terminator.

HDMA channels 1+2 change background color 0 per scanline group:
- Channel 1 writes 0 to CGADD (targets color 0)
- Channel 2 writes BGR555 to CGDATA

### Current gradient regions:
- Lines 1-44: Logo area (bright pink)
- Lines 45-54: Black transition
- Lines 55-67: Accent
- Lines 68-178: Graduated dark-to-bright ramp (text area)
- Lines 179+: Bottom border

### Designing a new gradient:
1. Choose a base hue
2. Create 10-12 steps from dark to bright
3. Logo area (first ~44 lines) = brightest
4. Ramp dark-to-bright over text area (~110 lines)
5. Bottom border accents

## Selection Bar: `snes/const.a65` labels `hdma_math_src` and `hdma_bar_color_src`

`hdma_bar_color_src` has two 4-byte entries (normal + highlight):
```
.byt $RR, $GG, $BB, $GG2  ; normal COLDATA values
.byt $RR, $GG, $BB, $GG2  ; highlight COLDATA values
```

COLDATA format ($2132): `[bit7=B][bit6=G][bit5=R][bits4-0=intensity]`
- `$3f` = R=31, `$5f` = G=31, `$9f` = B=31
- `$20` = R=0, `$40` = G=0, `$80` = B=0

## Workflow

When the user requests a new color scheme:
1. Convert requested colors to BGR555
2. Generate palette.a65 entries (if modifying text/logo colors)
3. Generate hdma_pal_src gradient table
4. Generate matching hdma_bar_color_src entries
5. Show values with comments
6. After editing, suggest `/build` then `/test` to preview
