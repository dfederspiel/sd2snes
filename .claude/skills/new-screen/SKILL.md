---
name: new-screen
description: Scaffold a new display screen for the SNES menu ROM. Use when adding a new UI screen, display mode, or information page.
argument-hint: "[screen-name]"
---

# Add a New Display Screen

Scaffold a new display screen for the sd2snes SNES menu ROM, following the pattern of `poc_display` in `snes/main.a65`.

## Architecture

Every screen follows the same pattern:
1. Set processor state (`sep`/`rep` for correct A/X/Y widths)
2. Render text via hiprint to WRAM tile buffers
3. Wait for NMI to DMA buffers to VRAM
4. Enter frame loop (wait for `isr_done` each frame)

## Template

See [templates/screen-template.a65](templates/screen-template.a65) for boilerplate code.

## Working Reference: poc_display

The existing `poc_display` in `snes/main.a65` (~line 121) is the canonical example:

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
  ; ... more hiprint calls ...
- lda isr_done
  lsr
  bcc -
  stz isr_done
  rts
```

## Steps to Add a New Screen

1. **Define strings** (in main.a65 or const.a65):
   ```asm
   my_str1  .byt "Title Text Here", 0
   my_str2  .byt "Description line", 0
   ```

2. **Write the display routine** using the template. Key points:
   - Start with `sep #$20 : .as` and `rep #$10 : .xl`
   - Row 9 = first row below logo area (rows 0-8 = logo)
   - Max ~26 visible characters per line (Mode 5)
   - print_pal: 0=normal, 1=bold
   - Always wait for isr_done after rendering

3. **Wire it up**:
   - Emulator mode: call from `emu_mode` in main.a65
   - MCU mode: call from filesel or menu code
   - Standalone: add branch after MCU check

4. **Ensure brightness**: verify `cur_bright`, `tgt_bright`, `bright_limit` >= `$0f`. Write `$2100` directly for immediate effect.

5. **Frame loop** (persistent display):
   ```asm
   - lda isr_done
     lsr
     bcc -
     stz isr_done
     bra -             ; infinite loop
   ```

6. **Input handling** (optional):
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

## Screen Layout

| Row | Content |
|-----|---------|
| 0-8 | Logo area (occupied by logo tilemap) |
| 9 | First usable text row |
| 10-28 | Main content area |
| 29-30 | Status bar area |

## Common Pitfalls

- Forgetting `rep #$10 : .xl` before `stx print_src` (corrupts print_src in 8-bit mode)
- Writing directly to VRAM instead of WRAM buffers (NMI overwrites VRAM)
- Not waiting for isr_done (text never appears)
- Forgetting null terminator on strings
- Setting brightness to 0 (always set both cur_bright AND tgt_bright)
