---
name: new-screen
description: Scaffold a new display screen for the SNES menu ROM. Use when adding a new UI screen, display mode, or information page.
argument-hint: "[screen-name]"
---

# Add a New Display Screen

Scaffold a new display screen for the sd2snes SNES menu ROM.

## Architecture

Every screen follows the same pattern:
1. Set processor state (`sep`/`rep` for correct A/X/Y widths)
2. Render text via hiprint to WRAM tile buffers
3. Wait for NMI to DMA buffers to VRAM
4. Enter frame loop (wait for `isr_done` each frame)

## 64tass Version (snes-64tass/)

The 64tass port's `poc_display` in `main.a65` is the primary reference. Key differences from snescom:

- No `:` chaining — `sep #$20` and `.as` on separate lines
- Bank extraction: `#label >> 16` instead of `#^label`
- Address extraction: `#label & $ffff` instead of `#!label`
- `.databank $7e` must be active for WRAM buffer access in hiprint
- Strings defined in `const.a65` with `.text "..."` + `.byte 0`

### 64tass Screen Layout

| Row | Content |
|-----|---------|
| 0-1 | Top gradient (Mode 5 starts at scanline 8) |
| 2-7 | Pink header area (title, subtitle, byline) |
| 8 | Transition line (pink-to-black border) |
| 9-28 | Main content area (dark gradient background) |
| 29-30 | Bottom border area |

### 64tass Template

```asm
my_screen
  ; Assumes: .databank $7e, sep #$20 (.as), rep #$10 (.xl)

  ; Title line at row 10
  lda #10
  sta print_y
  lda #3               ; left column
  sta print_x
  lda #my_string >> 16
  sta print_bank
  ldx #my_string & $ffff
  stx print_src
  lda #1               ; palette 1 = bold/highlight
  sta print_pal
  lda #32
  sta print_count
  jsr hiprint

  ; Wait one NMI for DMA to VRAM
- lda isr_done
  lsr
  bcc -
  stz isr_done
  rts
```

## snescom Version (snes/)

The snescom `poc_display` in `snes/main.a65` (~line 121) uses the original syntax:

```asm
poc_display:
  sep #$20 : .as       ; 8-bit accumulator
  rep #$10 : .xl       ; 16-bit index (needed for stx print_src)
  lda #10
  sta print_y
  lda #3
  sta print_x
  lda #^emu_str1
  sta print_bank
  ldx #!emu_str1
  stx print_src
  lda #1                ; palette 1 = bold
  sta print_pal
  lda #32
  sta print_count
  jsr hiprint
- lda isr_done
  lsr
  bcc -
  stz isr_done
  rts
```

### snescom Screen Layout

| Row | Content |
|-----|---------|
| 0-8 | Logo area (occupied by logo tilemap + sprites) |
| 9 | First usable text row |
| 10-28 | Main content area |
| 29-30 | Status bar area |

## Steps to Add a New Screen

1. **Define strings** in const.a65:
   - snescom: `.byt "Title Text Here", 0`
   - 64tass: `.text "Title Text Here"` then `.byte 0`

2. **Write the display routine** using the template above. Key points:
   - Max ~26 visible characters per line (Mode 5 pseudo-hires)
   - print_pal: 0=normal, 1=bold/highlight
   - Always wait for isr_done after rendering

3. **Wire it up**:
   - Emulator mode: call from `emu_mode` in main.a65
   - MCU mode: call from filesel or menu code
   - Standalone: add branch after MCU check

4. **Ensure brightness**: verify `cur_bright`, `tgt_bright` >= `$0f`. Write `$2100` directly for immediate effect if needed.

5. **Frame loop** (persistent display):
   ```asm
   - lda isr_done
     lsr
     bcc -
     stz isr_done
     bra -             ; infinite loop
   ```

6. **Input handling** (optional, requires pad.a65):
   ```asm
   - lda isr_done
     lsr
     bcc -
     stz isr_done
     jsr read_pad
     lda pad1trig
     and #$80          ; B button
     bne exit_screen
     bra -
   ```

## Common Pitfalls

- Forgetting `rep #$10` / `.xl` before `stx print_src` (corrupts print_src in 8-bit mode)
- Writing directly to VRAM instead of WRAM buffers (NMI overwrites VRAM every frame)
- Not waiting for isr_done (text never appears — DMA hasn't fired yet)
- Forgetting null terminator on strings
- Setting brightness to 0 (always set both cur_bright AND tgt_bright)
- In 64tass: missing `.databank $7e` directive (hiprint writes to WRAM buffers)
