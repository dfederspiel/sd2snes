# sd2snes Menu ROM - Development Guide

## Project Overview

sd2snes is a SNES flash cartridge with three tiers:
- **SNES Menu ROM** (`snes/`) - 65816 assembly, runs on the SNES itself as a real ROM
- **MCU Firmware** (`src/`) - ARM Cortex-M3/M4 C code, handles SD card, file I/O
- **FPGA** (`verilog/`) - Hardware logic for cartridge bus interface

This branch focuses on the SNES Menu ROM - the "game" that provides the file browser UI.

## Build System

### Toolchain
- **Assembler**: snescom 1.8.1.1 (65816 assembler by Bisqwit)
- **Linker**: sneslink (companion to snescom)
- **Preprocessor**: cpp (C preprocessor, used for macros/includes)
- **Location**: `/usr/local/bin/` in WSL Ubuntu 24.04
- **Source**: https://bisqwit.iki.fi/src/arch/snescom-1.8.1.1.tar.xz

### Build Command
```bash
wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes && make"
```

### Build Output
- `snes/menu.bin` - Menu ROM for sd2snes Mk.II (64KB HiROM)
- `snes/m3nu.bin` - Menu ROM for sd2snes Mk.III / FXPAK Pro (identical content)
- Both files are built identically; the MCU firmware hardcodes which filename to load
- Error 127 from `utils/mkmap.sh` is harmless (script not present in worktree)
- Warning "Short jump out of range" on certain lines is pre-existing and non-fatal

### Deploying to Physical Hardware
- **sd2snes Mk.II**: Copy `menu.bin` → SD card `/sd2snes/menu.bin`
- **sd2snes Mk.III / FXPAK Pro**: Copy `m3nu.bin` → SD card `/sd2snes/m3nu.bin`
- Back up the original file first! The MCU loads the menu ROM from SD card on every boot.
- Emulator-mode code won't activate on real hardware (MCU responds with $55)
- Palette and HDMA changes ARE visible on real hardware (shared code path)

## Testing in Emulator

### Emulator
- **bsnes-plus v05** (accuracy core) at `C:\Users\david\tools\bsnes-plus\extracted\bsnes-accuracy.exe`
- Launch: `start "" "./bsnes-accuracy.exe" "path/to/menu.bin"` from the bsnes directory
- Mesen2 v2.1.1 also available at `C:\Users\david\tools\mesen\extracted\` but bsnes-plus is preferred

### Cheat File
- `snes/menu.cht` - Loaded by bsnes alongside menu.bin
- Format: `"enabled","AAAAAAVV","description"` (6-hex address + 2-hex value)
- **Keep this file empty** for emulator mode detection to work
- Cheats in the $FF bank may not load in bsnes (limited address space support)

### Manifest
- `snes/menu.xml` - bsnes cartridge manifest defining memory mapping
- Declares HiROM layout, 64KB RAM at ff:0000-ffff, SRTC at 2800-2801

### Edit-Build-Test Loop (~15 seconds)
1. Edit `.a65` files in VS Code
2. Build: run the WSL make command above
3. Load `menu.bin` in bsnes-accuracy (File > Load Cartridge, or restart)

## Architecture: SNES Menu ROM

### Memory Map (key addresses from `memmap.i65`)
| Address | Name | Purpose |
|---------|------|---------|
| `$002A00` | MCU_CMD | Command register (SNES → MCU) |
| `$002A02` | SNES_CMD | Status register (MCU → SNES) |
| `$002A04` | MCU_PARAM | Parameter block (8 bytes) |
| `$002AFD` | WARM_SIGNATURE | Warm boot detection |
| `$FF0000` | FILESEL_CWD | Current working directory path |
| `$FF0100` | CFG_ADDR | Configuration block base |
| `$FF019D` | CFG_BRIGHTNESS_LIMIT | Screen brightness (0=unset) |
| `$C10000` | ROOT_DIR | Root directory listing from MCU |

### WRAM Layout (bank $7E)
| Address | Name | Purpose |
|---------|------|---------|
| `$7E0014` | print_x | hiprint X coordinate |
| `$7E0016` | print_y | hiprint Y coordinate (tile row) |
| `$7E0018` | print_src | hiprint string address (16-bit) |
| `$7E001A` | print_bank | hiprint string bank |
| `$7E001B` | print_pal | hiprint palette number |
| `$7E0022` | print_count | hiprint max chars |
| `$7E0027` | isr_done | NMI completion flag |
| `$7E0045` | pad1mem | Joypad current state |
| `$7E0047` | pad1trig | Joypad edge detection (newly pressed) |
| `$7EA000` | BG2_TILE_BUF | BG2 tile buffer (DMA'd to VRAM by NMI) |
| `$7EB000` | BG1_TILE_BUF | BG1 tile buffer (DMA'd to VRAM by NMI) |
| `$7EF000` | WRAM_ROUTINE | FPGA reconfig routine (copied from ROM) |
| `$7EF200` | WRAM_WAIT_MCU | MCU wait routine (copied from ROM) |

### VRAM Layout
| Address | Name | Purpose |
|---------|------|---------|
| `$5000` | BG2_TILE_BASE | BG2 tilemap |
| `$5800` | BG1_TILE_BASE | BG1 tilemap |
| `$6000` | OAM_TILE_BASE | Sprite tiles |

### Key Source Files

| File | Purpose |
|------|---------|
| `main.a65` | Entry point, init sequence, screen_on, emulator mode, setup_gfx |
| `header.a65` | ROM header, interrupt vectors, RESET entry |
| `reset.a65` | NMI_ROUTINE (VBlank handler), IRQ_ROUTINE |
| `dma.a65` | DMA helpers, setup_hdma (enables NMI), killdma |
| `dma.i65` | DMA7 macro for DMA transfers |
| `filesel.a65` | File selector: init, main loop, directory rendering |
| `ui.a65` | Text rendering: hiprint (Mode 5), loprint, draw_window |
| `palette.a65` | BGR555 palette data (512 bytes = 256 colors) |
| `const.a65` | String constants (null-terminated ASCII) |
| `data.a65` | WRAM variable declarations |
| `memmap.i65` | Memory map `#define` constants |
| `near.a65` | Tribute/splash screen (large graphics data) |
| `pad.a65` | Joypad reading |
| `font.a65` | Font tile data |
| `logo.a65` | Logo tile graphics |

### Boot Sequence (coldboot in `main.a65`)
```
RESET → GAME_MAIN → check WARM_SIGNATURE → coldboot
  1. killdma          - Stop all DMA channels
  2. clear_wram       - Zero all WRAM
  3. apu_ram_init     - Initialize APU
  4. waitblank        - Wait for VBlank
  5. snes_init        - Initialize all PPU registers, force blank on
  6. setup_gfx        - Load logo, fonts, palette, sprites to VRAM
  7. store_wram_routines - Copy MCU routines to WRAM
  8. colortest / video_init - Set BG mode 3, tilemap addresses, zero brightness vars
  9. setup_hdma       - Configure 6 HDMA channels, ENABLE NMI ($4200=$81)
  10. detect_ultra16 / detect_satellaview
  11. screen_on       - Set brightness to $0F, turn screen on
  12. wait_mcu_ready  - Poll SNES_CMD for $55 (with timeout)
  13. Check SNES_CMD:
      - $55 → normal MCU path (filesel_init → fileselloop)
      - else → emulator mode (poc_display)
```

### NMI Handler (`reset.a65` NMI_ROUTINE)
Fires every VBlank (~60Hz). Does:
1. DMA BG1_TILE_BUF and BG2_TILE_BUF from WRAM → VRAM (unless `screen_dma_disable` set)
2. Update cursor bar position from bar_yl/bar_xl
3. Screensaver idle detection (if CFG_ENABLE_SCREENSAVER)
4. Brightness fading: gradually moves cur_bright toward tgt_bright
5. Sets `isr_done = 1`

**Critical**: NMI DMAs WRAM tile buffers to VRAM every frame. Content must be written to WRAM buffers (via hiprint), not directly to VRAM, for it to persist.

### Text Rendering with hiprint (`ui.a65`)
Mode 5 pseudo-8x8 text using two BG layers. Setup pattern:
```asm
  lda #<row>          ; tile row (9+ for below logo)
  sta print_y
  lda #<col>          ; tile column (0 = left edge)
  sta print_x
  lda #^string_label  ; bank of string data
  sta print_bank
  ldx #!string_label  ; 16-bit address of string data
  stx print_src
  stz print_pal       ; palette 0 (or 1 for bold/highlight)
  lda #<max_chars>    ; max characters to print
  sta print_count
  jsr hiprint
```
Strings are null-terminated ASCII. Characters 0 and 1 = end of string.

### Palette Format (`palette.a65`)
- 512 bytes = 256 colors in BGR555 format (little-endian)
- Each color: 2 bytes, `0bbbbbgg_gggrrrrr` (15-bit, bit 15 unused)
- Color 0 of palette 0 = background/transparent color
- Example: `$00, $40` = dark blue (R=0, G=0, B=16)
- Example: `$1f, $00` = bright red (R=31, G=0, B=0)
- Example: `$ff, $7f` = white (R=31, G=31, B=31)
- Example: `$e0, $03` = bright green (R=0, G=31, B=0)

## HDMA Visual System (`dma.a65`, `const.a65`)

The menu's visual effects (gradient background, selection bar highlight) are driven by 6 HDMA channels configured in `setup_hdma`:

### Channels
| Channel | Registers | Purpose |
|---------|-----------|---------|
| 0 | $2105 (BGMODE) | Switches BG mode per scanline region |
| 1 | $2121 (CGADD) | Sets CGRAM address to 0 (targets bg color 0) |
| 2 | $2122 (CGDATA) | Writes BGR555 color to CGRAM (the gradient) |
| 3 | $210D (BG1HOFS) | BG1 horizontal scroll |
| 4 | $2111 (BG3VOFS) | BG3 vertical scroll |
| 5 | $2131+$2132 (CGADSUB+COLDATA) | Color math mode + fixed color |

### Background Gradient (Channels 1+2, `hdma_pal_src`)
Channel 1 always writes 0 to CGADD, channel 2 writes a 2-byte BGR555 color to CGDATA. Together they change background color 0 per scanline group, creating the vertical gradient behind the logo and file list.

Table format in `const.a65`: `scanline_count, low_byte, high_byte` repeated, terminated by `$00`.

Currently set to a **pink gradient** (R steps from 2→20, G from 0→5, B from 1→12).

### Color Math Bar (Channel 5, `hdma_math_src` + `hdma_bar_color_src`)
Channel 5 writes to $2131 (color math mode) and $2132 (COLDATA fixed color) per scanline. This creates the selection bar highlight and border tints.

COLDATA format: `[bit7=B plane][bit6=G plane][bit5=R plane][bits4-0=intensity]`
- `$3f` = R plane, intensity 31 (R=31)
- `$48` = G plane, intensity 8 (G=8)
- `$90` = B plane, intensity 16 (B=16)
- `$40` = G plane, intensity 0 (G=0, used to "turn off" the overlay)

### Modifying the Theme
To change the gradient color scheme, edit these in `const.a65`:
1. `hdma_pal_src` — the per-scanline BGR555 colors for the background gradient
2. `hdma_math_src` — initial color math values at screen top
3. `hdma_bar_color_src` — selection bar normal + highlight COLDATA values

The logo graphic (`logo.a65`) is hand-crafted 4bpp tile data (~14KB). PSD sources exist in `gfx/`. No automated image→tile converter exists in the repo — modifying the logo would require building a conversion pipeline.

## Emulator Mode (our addition)

Without the sd2snes hardware MCU, the menu ROM cannot communicate with the SD card. We added emulator detection that bypasses MCU-dependent code:

### How It Works
1. `wait_mcu_ready` polls SNES_CMD with a ~65536 iteration timeout
2. After timeout, `SNES_CMD != $55` → branch to `emu_mode`
3. `emu_mode` forces brightness to $0F and calls `poc_display`
4. `poc_display` renders text via hiprint, waits one NMI frame for DMA
5. Main loop: wait for isr_done each frame (NMI maintains display)

### Key Patches Made
- `screen_on`: Falls back to brightness $0F when CFG_BRIGHTNESS_LIMIT is 0
- `wait_mcu_ready`: Timeout after ~65536 polls instead of infinite loop
- `wram_wait_mcu_src`: Unchanged from original (infinite wait is correct — only called on real-hardware path)
- `emu_mode` / `poc_display`: New emulator-mode display path
- `menu.cht`: Must be empty (cheats bypass emulator detection)

## Common Pitfalls

### Black Screen Causes
1. **Force blank**: `$2100` bit 7 set ($80+) = screen off. `snes_init` sets $8F. Must write $0F later.
2. **Zero brightness**: cur_bright=0 causes NMI to maintain $2100=$00. Always set cur_bright AND tgt_bright.
3. **MCU infinite loops**: Any `SNES_CMD == $55` poll without timeout hangs forever in emulator.
4. **NMI overwrites VRAM**: NMI DMAs WRAM tile buffers → VRAM. If buffers are empty (after clear_wram), graphics get erased. Write to WRAM buffers via hiprint, not directly to VRAM.
5. **Cheat interference**: Old cheats in menu.cht (especially `002a0255`) force SNES_CMD=$55, making emulator detection fail.

### WRAM Routine Processor State Preservation
**Critical**: WRAM routines (`wram_wait_mcu_src`, `wram_routine_src`, etc.) are copied from ROM to WRAM at boot by `store_wram_routines` and called via `jsl`/`rtl` from various places in the codebase. These routines **must preserve the processor status register (P)** using `php`/`plp`.

**Why**: The 65816 processor flags (especially the M and X bits controlling 8/16-bit modes for accumulator and index registers) affect how subsequent instructions decode. If a WRAM routine changes processor modes internally (e.g., `rep #$10` for 16-bit index) without restoring them, the calling code silently breaks — `ldy #$0002` loads a 16-bit value instead of 8-bit, pointer arithmetic goes wrong, and the system crashes.

**Bug #1 (processor state)**: We added `rep #$10 : .xl` for a 16-bit timeout counter but didn't `php`/`plp`. On real hardware (where the MCU responds immediately), the function returned with X/Y in 16-bit mode. The caller in `filesel.a65` expected 8-bit index, causing file loading to black screen.

**Bug #2 (premature timeout)**: Even with `php`/`plp`, the ~65536 iteration timeout was too short for actual MCU operations (directory reads from SD card). The file list showed "Loading..." forever because the routine gave up before the MCU finished.

**Resolution**: Reverted `wram_wait_mcu_src` to the original infinite-wait loop. This is safe because the WRAM version is only called from the real-hardware code path (filesel.a65), never in emulator mode. Timeouts are only needed in `wait_mcu_ready` (the boot-time ROM routine used for emulator detection).

**Lesson**: Don't add timeouts to WRAM routines that are only used on the real-hardware path. The MCU *will* respond, but operations like SD card reads can take variable time. Timeouts belong in the boot-time detection code only.

**Pattern for safe WRAM routines** (if you do need to modify one):
```asm
wram_routine_src:
  php               ; ALWAYS save processor state first
  ; ... your code, free to change modes ...
  rep #$10 : .xl    ; safe to use 16-bit index here
  ; ... do work ...
  plp               ; ALWAYS restore before return
  rtl
```

**Also**: When changing a WRAM routine's size, update the corresponding `DMA7` copy size in `store_wram_routines`. The copy size must be ≥ the routine's actual byte count or the `rtl` at the end won't be copied and execution will run into garbage.

### Assembler Syntax Notes
- `@` prefix = long (24-bit) address: `lda @$FF019D`
- `!` prefix = absolute (16-bit) address: `ldx #!label`
- `^` prefix = bank byte of address: `lda #^label`
- `.as` = 8-bit accumulator mode, `.al` = 16-bit
- `.xs` = 8-bit index mode, `.xl` = 16-bit
- `sep #$20 : .as` = set 8-bit A (combined instruction + mode hint)
- `rep #$10 : .xl` = set 16-bit X/Y
- `- bra -` = branch to previous anonymous label (infinite loop)
- `+` = forward anonymous label, `-` = backward anonymous label
