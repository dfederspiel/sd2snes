# SNES Window Mask Reference

Source: Nintendo SNES Development Manual, Book I — Section 6 (Window), Section 6.3 (Setup Flowchart), Chapter 27 (Register Definitions), Appendix A.

## Overview

- **Two independent windows** (Window 1 and Window 2) define horizontal screen regions
- Windows mask **BG1-BG4**, **OBJ**, and **Color Math** independently
- Each target can use either or both windows with logic operations (OR, AND, XOR, XNOR)
- Windows define **horizontal** position only (left/right pixel columns per frame)
- For **vertical** variation, use HDMA to change window positions per scanline
- Complex shapes (circles, diamonds, spotlight) achieved by HDMA-driven position changes

## Window Concept

A window defines a horizontal range of pixels. Content can be shown **inside** or **outside** the window:

```
                    Window 1
           Left ($2126)    Right ($2127)
              |                |
  ──────────[=====VISIBLE=====]──────────  (IN mode)
  ═══VISIBLE═[────MASKED─────]═══VISIBLE═  (OUT mode)
```

When both windows are enabled, a **mask logic** operation (OR/AND/XOR/XNOR) combines them:

```
  Window 1:    [=======]
  Window 2:              [=======]
  OR:          [=================]     (union)
  AND:                                 (intersection — empty if non-overlapping)
  XOR:         [=======] [=======]     (one or the other)
  XNOR:       ═══════════════════      (neither or both)
```

## Registers

### Window Enable & IN/OUT Select

**$2123 — W12SEL** (BG1/BG2 window settings)
```
D7    D6      D5    D4      D3    D2      D1    D0
BG2   BG2     BG2   BG2     BG1   BG1     BG1   BG1
W2EN  W2I/O   W1EN  W1I/O   W2EN  W2I/O   W1EN  W1I/O
```

**$2124 — W34SEL** (BG3/BG4 window settings)
```
D7    D6      D5    D4      D3    D2      D1    D0
BG4   BG4     BG4   BG4     BG3   BG3     BG3   BG3
W2EN  W2I/O   W1EN  W1I/O   W2EN  W2I/O   W1EN  W1I/O
```

**$2125 — WOBJSEL** (OBJ and Color window settings)
```
D7    D6      D5    D4      D3    D2      D1    D0
COL   COL     COL   COL     OBJ   OBJ     OBJ   OBJ
W2EN  W2I/O   W1EN  W1I/O   W2EN  W2I/O   W1EN  W1I/O
```

For each target (BG1-BG4, OBJ, Color):
- **WxEN**: 0 = window disabled, 1 = window enabled
- **WxI/O**: 0 = mask **inside** window (IN), 1 = mask **outside** window (OUT)

**Note on IN/OUT terminology**: "IN" means the window region is where masking is applied — content is hidden inside the window. "OUT" means masking is applied outside — content is hidden outside the window (only visible inside).

Actually, the more intuitive way: when I/O=0 (IN), the area **inside** the window is the "masked" region. When I/O=1 (OUT), the area **outside** the window is the "masked" region. The "masked" region's effect depends on whether the layer is enabled in TMW/TSW.

### Window Position

| Register | Name | Purpose |
|----------|------|---------|
| $2126 | WH0 | Window 1 left position (0-255) |
| $2127 | WH1 | Window 1 right position (0-255) |
| $2128 | WH2 | Window 2 left position (0-255) |
| $2129 | WH3 | Window 2 right position (0-255) |

- Each position is 8-bit (0-255 pixel columns)
- **If left > right**: window has no active range (effectively disabled)
- This is the standard way to "turn off" a window without touching enable bits

### Window Mask Logic

**$212A — WBGLOG** (BG1-BG4 logic)
```
D7  D6    D5  D4    D3  D2    D1  D0
BG4 logic BG3 logic BG2 logic BG1 logic
```

**$212B — WOBJLOG** (OBJ and Color logic)
```
D7-D4  unused   D3  D2       D1  D0
                 COL logic   OBJ logic
```

Logic codes (2-bit per target):

| D1 D0 | Logic | Effect (both windows IN) |
|--------|-------|--------------------------|
| 00 | OR | Union — masked where either window covers |
| 01 | AND | Intersection — masked only where both overlap |
| 10 | XOR | Exclusive — masked where one but not both covers |
| 11 | XNOR | Negation of XOR — masked where both or neither covers |

**Note**: Logic only applies when both Window 1 and Window 2 are enabled for a target. If only one window is enabled, the logic setting is ignored.

### Window Mask Designation (Through Main/Sub)

**$212E — TMW** (Main screen window mask)
```
D7-D5  unused   D4     D3    D2    D1    D0
                 OBJ    BG4   BG3   BG2   BG1
```

**$212F — TSW** (Sub screen window mask)
```
D7-D5  unused   D4     D3    D2    D1    D0
                 OBJ    BG4   BG3   BG2   BG1
```

- Bit = 0: Layer ignores window masking (layer drawn everywhere)
- Bit = 1: Layer is affected by its window settings ($2123-$2125)

**Important**: A layer must be enabled in both $212C/$212D (TM/TS) AND $212E/$212F (TMW/TSW) for window masking to take effect.

## Color Window ($2130)

The Color Window controls where color math (addition/subtraction) is applied. It uses the same Window 1/2 mechanism via $2125 bits D7-D4.

**$2130 — CGWSEL** (Color math window control)
```
D7  D6      D5  D4        D3-D2   D1    D0
Clip main   Prevent sub   unused  CC    Direct
```

- **Clip main (D7-D6)**: Controls when main screen is forced to black
  - 00 = never clip
  - 01 = clip outside color window
  - 10 = clip inside color window
  - 11 = always clip (entire main screen is black)

- **Prevent sub (D5-D4)**: Controls when color math is prevented
  - 00 = never prevent (math always applies where enabled)
  - 01 = prevent outside color window
  - 10 = prevent inside color window
  - 11 = always prevent (no color math anywhere)

- **CC (D1)**: 0 = add/subtract with sub screen, 1 = add/subtract with fixed color ($2132)
- **Direct (D0)**: Direct color mode for Modes 3/4/7

### Color Math Interaction with Windows

The Color Window creates regions where color math is applied or suppressed. This enables effects like:
- **Spotlight**: Color math darkens everything outside a moving window
- **Tinted region**: Only a specific horizontal band gets color-shifted
- **Selection bar**: The sd2snes menu uses this — the cursor bar is a color math window

## sd2snes Menu Window Usage

The menu uses Window 1 for the **selection bar highlight**:

### NMI Handler (reset.a65)
```asm
; Calculate cursor bar physical position from logical position
  lda bar_xl          ; get logical cursor X pos
  asl
  dec
  asl
  sta bar_x           ; physical pos = logical pos * 4 - 2
  sta $2126           ; Window 1 left position

  lda bar_wl          ; get logical cursor width
  asl
  asl                 ; pixel width = logical width * 4 + 1
  inc
  sta bar_w
  clc
  adc bar_x           ; + X start coord
  sta $2127           ; Window 1 right position
```

### HDMA Color Math (Channel 5)
The color math HDMA (channel 5 in `setup_hdma`) writes to $2131 (CGADSUB) and $2132 (COLDATA) per scanline group. Combined with the window positions set by NMI, this creates the colored selection bar:

```
Scanline regions (from hdma_math_src):
  - Region above bar: color math off ($00 to $2131)
  - Bar top border: R=31 → G=8 → sub half + B=16 (warm pink tint)
  - Bar body: sub half + G=0 (darker tint)
  - Bar bottom border: different math mode
  - Region below bar: color math off
```

The NMI handler dynamically rewrites the HDMA table's scanline counts to position the bar at the correct Y location.

### Disabling the Window (Gotcha)

When the selection bar is hidden (bar_wl=0), the NMI's position math can produce a small non-zero window at the screen edge, causing a visible artifact. The fix: when bar_wl=0, explicitly set left > right to disable the window:

```asm
  lda bar_wl
  beq +               ; if width = 0, skip
  ; ... normal window setup ...
  bra window_done
+ lda #$01
  sta $2126           ; left = 1
  stz $2127           ; right = 0 → window disabled
window_done
```

## Official Setup Sequence (from Manual Section 6.3)

Nintendo's prescribed order for setting up window masking:

### Phase 1: Initial Settings
```
1. Clear each register (snes_init)
2. Set main screen layer enables ($212C — TM)
   - Enable BG/OBJ layers that will be displayed
3. Set $2123-$2125 (window enable and IN/OUT per layer)
   - Choose which windows affect which layers
   - Choose IN or OUT masking direction
4. Set $2126-$2129 (window positions)
   - Window 1: left and right pixel positions
   - Window 2: left and right pixel positions
5. Set $212A/$212B (mask logic)
   - Choose OR/AND/XOR/XNOR for each layer
6. Set $212E/$212F (TMW/TSW)
   - Enable window masking on main and/or sub screen per layer
```

### Phase 2: V-Blank / HDMA
```
7. If using dynamic windows (per-scanline changes):
   - Set up HDMA channel targeting $2126-$2129
   - HDMA table changes left/right positions each scanline
   - Enable HDMA via $420C
8. Display (turn off forced blank: $2100 = $0F)
```

## Quick Recipes

### Simple Color Window (Darken Outside a Region)

```asm
; Darken everything outside a 100-pixel wide band centered at pixel 128
  lda #$22            ; BG1+BG2 on main screen
  sta $212C

; Enable Color Window using Window 1
  lda #$02            ; Color: W1 enabled, IN mode
  sta $2125

; Window 1 position: pixels 78-178
  lda #78
  sta $2126           ; left
  lda #178
  sta $2127           ; right

; Color math: subtract, half, apply to backdrop
  lda #$e0            ; subtract + half + backdrop
  sta $2131

; Fixed color = dark (subtract all channels by 16)
  lda #$b0            ; B=16
  sta $2132
  lda #$50            ; G=16
  sta $2132
  lda #$30            ; R=16
  sta $2132

; Prevent color math inside window (only darken outside)
  lda #$10            ; prevent sub inside window (D5-D4 = 01)
  sta $2130

; Enable window masking for color on main screen
; (Note: color window uses $2130 clip/prevent, not TMW)
```

### HDMA-Driven Circular Window

To create a circle/spotlight effect, set up HDMA on $2126/$2127 (Window 1 positions) with a table that varies left/right per scanline to trace a circular shape:

```asm
; HDMA channel targeting $2126 (WH0) and $2127 (WH1)
; Transfer mode $01 = 2 bytes → reg, reg+1
  lda #$01            ; mode 1: 2 bytes, 2 registers
  sta $4300
  lda #$26            ; B-bus = $2126 (WH0), auto WH1
  sta $4301
  lda #^circle_table
  ldy #!circle_table
  sty $4302
  sta $4304

; circle_table: scanline_count, left, right per entry
; Shape a circle by varying left/right symmetrically
circle_table
  .byt 10, 128, 128   ; top: window closed (no visible area)
  .byt  1, 118, 138   ; narrow opening
  .byt  1, 110, 146
  .byt  1, 104, 152   ; widening
  .byt  1, 100, 156
  ; ... mirror for bottom half ...
  .byt $00             ; end
```

## Window Logic Truth Tables

For reference, all combinations when both Window 1 and Window 2 are enabled as IN:

```
Position:  | In W1 only | In both | In W2 only | In neither |
-----------+------------+---------+------------+------------|
OR  result | masked     | masked  | masked     | not masked |
AND result | not masked | masked  | not masked | not masked |
XOR result | masked     | not     | masked     | not masked |
XNOR result| not masked | masked  | not masked | masked     |
```

When windows use different IN/OUT settings, the individual window regions are inverted before logic is applied.
