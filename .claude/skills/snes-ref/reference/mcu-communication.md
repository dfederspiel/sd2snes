# SNES ROM ↔ MCU Communication via FPGA

The sd2snes has three processors that must cooperate: the **SNES CPU** (65816), the **MCU** (ARM Cortex-M3/M4), and the **FPGA** (cartridge bus logic). They communicate through shared memory regions that the FPGA maps into the SNES address space.

## Architecture Overview

```
+----------+     SNES Bus     +----------+     SPI     +----------+     SD/MMC
| SNES CPU | <--------------> |   FPGA   | <---------> |   MCU    | <---------> SD Card
| (65816)  |   $002Axx R/W    | (bridge) |  snescmd_*  | (ARM C)  |    fatfs
+----------+   $C0xxxx R/W    +----------+  sram_r/w   +----------+
                                   |
                              +----------+
                              |   SRAM   |  16MB address space
                              | (shared) |  $000000-$FFFFFF
                              +----------+
```

The FPGA exposes two shared memory regions:
1. **BRAM (Block RAM)** at `$002A00-$002CFF` — ~768 bytes of fast FPGA-internal RAM
2. **SRAM** at `$000000-$FFFFFF` — 16MB address space, holds ROM image, config, directory data, and more

## SRAM: The 16MB Shared Memory Space

### Physical SRAM

The FPGA maps a 24-bit (16MB) address space. The MCU accesses it via SPI commands (`set_mcu_addr()` + `FPGA_TX_BYTE(0x98)` for write, `0x88` for read). The SNES accesses it directly via the cartridge bus (long addressing like `lda @$C10000`).

**Arbitration**: The FPGA handles bus arbitration transparently — no explicit mutex or handshake in firmware. The design relies on non-overlapping access patterns: the MCU writes to one SRAM region while the SNES reads from another, and the command protocol ensures they don't collide on the same region simultaneously.

### Complete SRAM Memory Map

Source: `src/memory.h`

| Address | End | MCU Define | Size | Purpose | Status |
|---------|-----|-----------|------|---------|--------|
| `$000000` | `$BFFFFF` | `SRAM_ROM_ADDR` | Up to 12MB | Game ROM image | Active — loaded by LOADROM |
| `$C00000` | `$C0FFFF` | `SRAM_MENU_ADDR` | 64KB | Menu ROM binary | Active — our code lives here |
| `$C10000` | `$C7FFFF` | `SRAM_DIR_ADDR` | ~448KB | Directory listing | Active — READDIR writes here |
| `$C80000` | `$CFFFFF` | `SRAM_DB_ADDR` | 512KB | Database | **Reserved, unused** |
| `$CFFFFE` | `$CFFFFF` | `SRAM_NUM_CHEATS` | 2 bytes | Cheat count | Active |
| `$D00000` | `$DFFFFF` | `SRAM_CHEAT_ADDR` | 1MB | Cheat code data | Active — LOAD_CHT |
| `$E00000` | `$EFFFFF` | `SRAM_SAVE_ADDR` | 1MB | Game save RAM | Active — battery saves |
| `$F00000` | `$FCFFFF` | `SRAM_SKIN_ADDR` | ~832KB | **Skin graphics** | **Defined but UNUSED** |
| `$FD0000` | `$FDFFF` | `SRAM_SPC_DATA_ADDR` | 64KB | SPC audio data | Active — LOADSPC |
| `$FE0000` | `$FE0FFF` | `SRAM_SPC_HEADER_ADDR` | 4KB | SPC header + DSP regs | Active — LOADSPC |
| `$FE1000` | `$FEFFFF` | `SRAM_SAVESTATE_HANDLER_ADDR` | ~60KB | Savestate handler code | Active |
| `$FF0000` | `$FF00FF` | `SRAM_MENU_FILEPATH_ADDR` | 256 bytes | Current directory path | Active |
| `$FF0100` | `$FF019C` | `SRAM_MENU_CFG_ADDR` | ~157 bytes | Configuration block (`cfg_t`) | Active |
| `$FF1000` | `$FF1003` | `SRAM_CMD_ADDR` | 4 bytes | MCU boot message area | Active |
| `$FF1004` | `$FF1007` | `SRAM_PARAM_ADDR` | 4 bytes | Command parameters | Active |
| `$FF1100` | `$FF110F` | `SRAM_MCU_STATUS_ADDR` | 16 bytes | MCU → SNES status | Active |
| `$FF1110` | `$FF111F` | `SRAM_SNES_STATUS_ADDR` | 16 bytes | SNES → MCU status | Active |
| `$FF1200` | `$FF141F` | `SRAM_SYSINFO_ADDR` | 544 bytes | System info display | Active |
| `$FF1420` | `$FF3FFF` | `SRAM_LASTGAME_ADDR` | ~10.5KB | Recent games list | Active |
| `$FF4000` | `$FFFEFF` | `SRAM_FAVORITEGAMES_ADDR` | ~48KB | Favorite games list | Active |
| `$FFFF00` | `$FFFEFF` | `SRAM_SCRATCHPAD` | 256 bytes | MCU temporary storage | Active |
| `$FFFFF0` | `$FFFFF7` | `SRAM_DIRID` | 8 bytes | Directory navigation ID | Active |

### Free Regions for New Features

| Address Range | Size | Notes |
|--------------|------|-------|
| `$C80000-$CFFFFD` | ~512KB | `SRAM_DB_ADDR` — reserved for "database", never implemented |
| `$F00000-$FCFFFF` | ~832KB | `SRAM_SKIN_ADDR` — reserved for "skins", never implemented |

The **skin region** at `$F00000` is particularly interesting:
- `cfg_t` in `src/cfg.h` has a `skin_name[128]` field for a skin filename
- `filetypes.c` recognizes `TYPE_SKIN` (.SKIN files) in directory listings
- **No code exists** that reads or writes skin data to this SRAM region
- This was clearly planned for custom menu themes — exactly what we'd want for image loading

### SNES Access to SRAM

The SNES reads SRAM via long addressing (24-bit). Key patterns from the menu ROM:

```asm
; Read a byte from config block
lda @CFG_BRIGHTNESS_LIMIT    ; lda $FF019D (long absolute)

; Read directory data
lda @ROOT_DIR,x              ; lda $C10000,x (long indexed)

; Write CWD path
sta @FILESEL_CWD,x           ; sta $FF0000,x
```

**DMA from SRAM**: The SNES can DMA directly from any SRAM bank to WRAM or VRAM. The directory listing data at `$C10000` is read character-by-character via hiprint (not bulk DMA'd), but there's no technical reason you couldn't DMA a block of SRAM tile data directly to VRAM:

```asm
; Hypothetical: DMA pre-converted tile data from SRAM to VRAM
ldx #$0000
stx $2116            ; VRAM address
DMA7 $01, tile_size, ^SRAM_SKIN_ADDR, !SRAM_SKIN_ADDR, $18
```

## BRAM: The Command Channel ($002A00-$002CFF)

BRAM is ~768 bytes of fast FPGA-internal RAM, the primary communication mechanism between SNES and MCU. The FPGA maps it into SNES address space at `$002A00`. The MCU accesses it via SPI commands.

### Command Registers

| SNES Address | MCU Name | Size | Direction | Purpose |
|-------------|----------|------|-----------|---------|
| `$002A00` | `SNESCMD_MCU_CMD` | 1 byte | SNES → MCU | SNES writes command byte here |
| `$002A02` | `SNESCMD_SNES_CMD` | 1 byte | MCU → SNES | MCU writes status/ACK here |
| `$002A04` | `SNESCMD_MCU_PARAM` | ~252 bytes | Bidirectional | Command parameters (to $2AFF) |

**Parameter space**: The BRAM parameter area at `$2A04` extends to `$2AFF` — approximately **252 bytes** of parameter data per command. Commands like READDIR use offsets +0 through +12 within this space.

### MCU Access Functions (src/snes.c)

```c
// Byte-level BRAM access
fpga_set_snescmd_addr(addr);     // Set BRAM address pointer
fpga_read_snescmd();             // Read 1 byte
fpga_write_snescmd(val);         // Write 1 byte

// Block access (loops byte-by-byte via SPI)
snescmd_readblock(buf, addr, len);   // Read block from BRAM
snescmd_writeblock(buf, addr, len);  // Write block to BRAM
snescmd_readstrn(buf, addr, maxlen); // Read null-terminated string

// Convenience
snescmd_writebyte(val, addr);
snescmd_readbyte(addr);
```

**Block transfer limit**: Practical max ~512-1024 bytes (limited by MCU RAM buffers). For large data, use SRAM (`sram_readblock`/`sram_writeblock`) instead.

### SRAM Access Functions (src/memory.c)

```c
// Large block transfers (max 65535 bytes per call)
sram_readblock(buf, addr, size);    // Read SRAM → MCU buffer
sram_writeblock(buf, addr, size);   // Write MCU buffer → SRAM

// Streaming write (used by LOADSPC, LOADROM)
set_mcu_addr(sram_addr);
FPGA_SELECT();
FPGA_TX_BYTE(0x98);                // Write mode
for (j = 0; j < len; j++) {
    FPGA_TX_BYTE(data[j]);
    FPGA_WAIT_RDY();               // SPI sync after each byte
}
FPGA_DESELECT();

// SD card file I/O
f_open(&file_handle, path, FA_READ);
file_read();                        // Reads up to 512 bytes into file_buf
file_getc();                        // Single byte with 512-byte internal buffer
```

## Complete MCU Command Table

Source: `src/snes.h`, dispatched in `src/main.c`

### Menu Mode Commands (SNES → MCU)

| Code | Name | Parameters | SRAM Written | Timing |
|------|------|-----------|-------------|--------|
| `$01` | `LOADROM` | Path in BRAM+CWD | ROM → `$000000` | 1-10s |
| `$02` | `SETRTC` | 12 bytes RTC data in BRAM | — | <1ms |
| `$03` | `SYSINFO` | — | Sysinfo → `$FF1200` (continuous) | Ongoing |
| `$04` | `LOADLAST` | 1-byte game index | ROM → `$000000` | 1-10s |
| `$05` | `LOADSPC` | Path in BRAM+CWD | SPC → `$FD0000`, hdr → `$FE0000` | 100-500ms |
| `$06` | `LOADFAVORITE` | 1-byte fav index | ROM → `$000000` | 1-10s |
| `$07` | `SET_ALLOW_PAIR` | 1-byte flag | — | <1ms |
| `$08` | `SET_VIDMODE_GAME` | 1-byte mode | — | <1ms |
| `$09` | `SET_VIDMODE_MENU` | 1-byte mode | — | <1ms |
| `$0A` | `READDIR` | Path+target+filter (see below) | Dir → `$C10000` | 50-200ms |
| `$0B` | `FPGA_RECONF` | — | — | ~100ms |
| `$0C` | `LOAD_CHT` | — | Cheats → `$D00000` | 10-100ms |
| `$0D` | `SAVE_CHT` | — | (reads from SRAM) | 10-100ms |
| `$0E` | `SAVE_CFG` | — | (reads from SRAM) | 10-50ms |
| `$12` | `LED_BRIGHTNESS` | 1-byte level | — | <1ms |
| `$13` | `ADD_FAVORITE` | — | Favorites → `$FF4000` | 10-50ms |
| `$14` | `REMOVE_FAVORITE` | 1-byte index | Favorites → `$FF4000` | 10-50ms |

### Game Mode Commands

| Code | Name | Purpose |
|------|------|---------|
| `$40` | `SAVESTATE` | Save game state to SD |
| `$41` | `LOADSTATE` | Load game state from SD |
| `$80` | `RESET` | Pulse SNES reset |
| `$81` | `RESET_TO_MENU` | Reset + return to menu |
| `$82` | `ENABLE_CHEATS` | Enable WRAM cheat patching |
| `$83` | `DISABLE_CHEATS` | Disable WRAM cheat patching |
| `$84` | `KILL_NMIHOOK` | Disable NMI hook entirely |
| `$85` | `TEMP_KILL_NMIHOOK` | Temporarily disable NMI hook |

### MCU Responses (written to SNES_CMD $2A02)

| Value | Meaning |
|-------|---------|
| `$55` | Ready / ACK |
| `$AA` | Error |
| `$77` | FPGA reconfig complete |
| Other | Echo of command byte (transient) |

### Command Dispatch Loop (src/main.c)

The MCU runs a continuous polling loop with no explicit delay:

```c
while (!cmd) {
    snescmd_writebyte(MCU_CMD_RDY, SNESCMD_SNES_CMD);  // Signal $55
    cmd = menu_main_loop();      // Poll MCU_CMD (microsecond latency)
    echo_mcu_cmd();              // Echo command to SNES_CMD
    switch (cmd) { /* dispatch */ }
}
```

**Response latency**: Microseconds from SNES writing MCU_CMD to MCU reading it. The bottleneck is always the operation itself (SD card reads), not the command dispatch.

## READDIR: Model for SD → SRAM Data Transfer

READDIR is the most relevant command for understanding how to build new data loading features. It demonstrates the full pattern: SNES sets parameters in BRAM → MCU reads SD card → MCU writes structured data to SRAM → SNES reads from SRAM.

### SNES Side (filesel.a65)

```asm
; Set parameters in BRAM
; +0: 24-bit pointer to CWD path string in SRAM
; +4: 24-bit target SRAM address for output
; +8: file type filter bytes (TYPE_PARENT, TYPE_SUBDIR, TYPE_ROM, etc.)
; +12: terminator ($00)

lda #CMD_READDIR
sta @MCU_CMD            ; Write command to $002A00

; Wait for MCU to finish
jsl WRAM_WAIT_MCU       ; Polls SNES_CMD for $55
```

### MCU Side (src/main.c)

```c
void menu_cmd_readdir(void) {
    uint8_t path[256];
    SNES_FTYPE filetypes[16];

    snes_get_filepath(path, 256);                              // Read path from BRAM param +0
    snescmd_readstrn(filetypes, SNESCMD_MCU_PARAM + 8, 16);   // Read filter from BRAM param +8
    uint32_t tgt_addr = snescmd_readlong(SNESCMD_MCU_PARAM + 4) & 0xffffff;

    scan_dir(path, tgt_addr, filetypes);  // Read SD directory, write to SRAM
}
```

### Output Format in SRAM

READDIR writes a two-table structure to SRAM:

**Pointer table** (at target address, e.g., `$C10000`):
- 4-byte entries: `[offset_lo, offset_mid, offset_hi, file_type]`
- Offset is relative to `SRAM_MENU_ADDR` ($C00000)
- Terminated by 4 zero bytes

**File data table** (at target + `$10000`, e.g., `$C20000`):
- Variable-length entries: `[6-byte size string][null-terminated filename]`
- Size string examples: `" 1024k"`, `" <dir>"`

### File Type Enum (src/filetypes.h)

| Value | Name | Extensions |
|-------|------|-----------|
| `$00` | `TYPE_UNKNOWN` | (skipped) |
| `$01` | `TYPE_ROM` | .smc, .sfc, .fig, .swc, .bs, .gb, .gbc, .sgb |
| `$02` | `TYPE_SUBDIR` | (directories) |
| `$03` | `TYPE_PARENT` | (..) |
| `$04` | `TYPE_SPC` | .spc |
| `$05` | `TYPE_CHT` | .yml (cheat files) |
| `$06` | `TYPE_SKIN` | .skin |

## LOADSPC: Model for "Load File to Fixed SRAM Address"

LOADSPC shows how the MCU streams a file from SD card directly to SRAM. This is the simplest model for a "load image data" command.

Source: `src/memory.c:572-647`

### Flow

1. SNES writes `$05` to MCU_CMD
2. MCU opens SPC file from SD card (path from BRAM parameters)
3. MCU validates file size (min 65920 bytes for valid SPC)
4. **Streams 64KB of SPC data** from SD → SRAM at `$FD0000`:
   ```c
   set_mcu_addr(spc_data_addr);   // $FD0000
   FPGA_SELECT();
   FPGA_TX_BYTE(0x98);            // SPI write mode
   for (j = 0; j < bytes_read; j++) {
       FPGA_TX_BYTE(file_buf[j]); // 512-byte chunks from SD
       FPGA_WAIT_RDY();
   }
   FPGA_DESELECT();
   ```
5. Writes 256-byte SPC header to `$FE0000`
6. Writes 128-byte DSP register block to `$FE0100`
7. Signals completion by writing `$55` to SNES_CMD

### Key Implementation Details

- **512 bytes per SD read**: `file_read()` fills a 512-byte `file_buf`, then streams it to SRAM byte-by-byte via SPI
- **No size limit**: The loop continues until EOF; files up to 16MB could theoretically be loaded
- **Fixed target address**: Hardcoded to `SRAM_SPC_DATA_ADDR` — a generic version would take the target address as a parameter

## Command Protocol Patterns

### Pattern 1: Simple Command (instant)

```
SNES: sta MCU_CMD [$07 = SET_ALLOW_PAIR]
MCU:  reads cmd, executes immediately
MCU:  writes $55 → SNES_CMD
SNES: reads SNES_CMD == $55, continues
```

### Pattern 2: Data Load (SD card involved)

```
SNES: writes parameters to BRAM ($2A04+)
SNES: sta MCU_CMD [$0A = READDIR]
SNES: calls WRAM_WAIT_MCU (polls SNES_CMD for $55)
MCU:  reads params from BRAM
MCU:  reads SD card (50-200ms)
MCU:  writes data to SRAM
MCU:  writes $55 → SNES_CMD
SNES: SNES_CMD == $55, reads data from SRAM
```

### Pattern 3: Multi-phase (game launch)

```
SNES: sta MCU_CMD [$01 = LOADROM]
MCU:  loads ROM to SRAM (1-10s)
MCU:  writes $55 → SNES_CMD
SNES: sta MCU_CMD [$0B = FPGA_RECONF]
MCU:  reconfigures FPGA
MCU:  writes $77 → SNES_CMD
SNES: copies fadeloop to BRAM, fades screen
SNES: sta MCU_CMD [$80 = RESET]
MCU:  resets SNES, installs nmihook, deasserts reset
```

## BRAM: The NMI Hook System ($002A10-$002AFF)

After a game loads, the FPGA intercepts the game's NMI vector and redirects it to code stored in BRAM. This code provides:
- In-game button combos (reset to menu, enable/disable cheats)
- WRAM cheat patching
- Savestate support
- Joypad reading (auto-joypad or manual)

### How the NMI Hook Gets Installed

**Source**: The menu ROM contains ~240 bytes of NMI/reset hook code.

**Pointer at $C0FF00**: The ROM at `$C0FF00` contains a 16-bit word pointing to the hook code:
```asm
* = $C0FF00
nmihook_ptr
  .word nmihook & $ffff    ; MCU reads from $C0xxxx in SRAM
```

**MCU reads the pointer** during `init()` (after SNES reset, before deassert_reset):
```c
void snescmd_prepare_nmihook() {
    uint16_t bram_src = sram_readshort(SRAM_MENU_ADDR + MENU_ADDR_BRAM_SRC);
    uint8_t bram[BRAM_SIZE];  // BRAM_SIZE = 240
    sram_readblock(bram, SRAM_MENU_ADDR + bram_src, BRAM_SIZE);
    snescmd_writeblock(bram, SNESCMD_INGAME_HOOK, BRAM_SIZE);
}
```

**FPGA patches branches**: The hook code contains `bra` instructions at fixed byte offsets that the FPGA patches at runtime. The byte positions are hardcoded in the FPGA verilog.

### BRAM Memory Map During Gameplay

| SNES Address | MCU Name | Purpose |
|-------------|----------|---------|
| `$002A10` | `SNESCMD_INGAME_HOOK` | NMI hook entry point |
| `$002A7D` | `SNESCMD_RESET_HOOK` | Reset hook |
| `$002AD8` | `SNESCMD_WRAM_CHEATS` | WRAM cheat patch code |
| `$002BA0` | `SNESCMD_NMI_RESET` | Reset command word |
| `$002BF0` | `NMI_PAD` | Joypad state |
| `$002BF2` | `NMI_CMD` | NMI command |
| `$002BFC` | `NMI_BUTTONS_ENABLE` | Button enable flag |
| `$002BFD` | `NMI_VECT_DISABLE` | Disable NMI redirect |
| `$002BFE` | `NMI_WRAM_PATCH_DISABLE` | WRAM patch disable |
| `$002BFF` | `NMI_WRAM_PATCH_COUNT` | Active cheat count |
| `$002C00` | `SNESCMD_EXE` | Executable code area |

### BRAM During Game Launch (Temporary Reuse)

BRAM is temporarily repurposed during game launch:
1. `game_handshake`: SNES communicates via MCU_CMD/SNES_CMD
2. After FPGA reconfig: SNES copies `fadeloop` routine to BRAM ($002A10)
3. `fadeloop` executes from BRAM: fades screen, fills WRAM, sends CMD_RESET
4. MCU's `init()` overwrites BRAM with nmihook code
5. Game boots: FPGA redirects NMI to hook code in BRAM

## Designing New Data Transfer Features

### What's Possible Without MCU Firmware Changes

The existing command set can already support some image loading patterns:

1. **LOADSPC pattern**: If image data were stored as `.spc` files (or the SPC slot is temporarily repurposed), the SNES could use CMD_LOADSPC to load 64KB to `$FD0000`, then DMA from there to VRAM. **Hack-ish but functional.**

2. **Pre-loaded data in menu ROM**: Images smaller than ~32KB could be embedded in the 64KB menu ROM itself and accessed directly from bank $C0. **Limited by ROM space.**

3. **SRAM_SKIN_ADDR**: The skin region at `$F00000` is already allocated. If a skin loader were added to the MCU firmware, it would be a natural fit.

### What Would Require MCU Firmware Changes

A proper image gallery would need:

```
New command: CMD_LOAD_BLOCK ($XX)
Parameters:
  +0: 24-bit SRAM target address (e.g., $F00000)
  +4: null-terminated filename path
MCU action:
  1. Open file from SD card
  2. Stream entire file contents to target SRAM address
  3. Signal $55 when done
SNES action:
  1. Set params in BRAM
  2. Write CMD_LOAD_BLOCK to MCU_CMD
  3. Wait for $55
  4. DMA from SRAM target to VRAM
```

This is essentially LOADSPC but with a configurable target address and no format-specific parsing. The MCU firmware change would be ~20 lines of C in the command dispatch switch.

### Bandwidth Estimates

- **SD → SRAM**: ~200-500 KB/s (SPI bottleneck, byte-at-a-time with FPGA_WAIT_RDY)
- **SRAM → VRAM via DMA**: ~2.68 MB/s (SNES DMA rate, limited to VBlank)
- **Loading a 32KB 4bpp tile set**: ~60-160ms from SD → SRAM
- **DMA 32KB SRAM → VRAM**: ~12ms (fits in one VBlank)

A gallery could show a new image every ~200ms from button press — fast enough to feel responsive.

## The $55 Trap

The MCU writes `$55` to SNES_CMD at **two different points**:
1. **Boot ready signal** — `main.c:286`: tells the menu ROM the MCU is alive
2. **LOADROM ACK** — `memory.c:300`: inside `load_rom()` when done loading

The SNES side (`game_handshake`) polls for `$55` as the ACK. It does NOT get $55 from `echo_mcu_cmd()` — that echoes the command byte back, which the SNES ignores while polling.

## Critical Lesson: The ROM Binary Is an API

The menu ROM is not just SNES code — it's also a **data source** that the MCU reads from. The MCU treats specific ROM offsets as structured data:

| ROM Offset | MCU Reads | What It Expects |
|-----------|-----------|-----------------|
| `$C0FF00` | `snescmd_prepare_nmihook()` | 16-bit pointer to 240 bytes of NMI hook code |
| `$FF0000` | `get_selected_name()` (via BRAM param) | Null-terminated CWD path string |
| `$FF0100` | config system | Configuration structure (`cfg_t`, ~157 bytes) |
| `$FF1110` | `status_save_from_menu()` | 3-byte snes_status_t (Ultra16, Satellaview flags) |

If ANY of these offsets contain wrong data, the MCU will silently use garbage values. There are no checksums or validation.

## Debugging Checklist

When game launching fails (black screen after file selection):

1. **Check nmihook_ptr at $C0FF00**: Must be a valid 16-bit offset into the ROM. Zero = broken.
2. **Verify nmihook data at the pointed offset**: The 240 bytes must be actual 65816 hook code.
3. **Check fadeloop copies correctly**: MVN operands reversed in 64tass vs snescom.
4. **Check WRAM routines are present**: DMA7 sizes in `store_wram_routines` must match actual routine sizes.
5. **Check SRAM status flags**: `detect_ultra16`/`detect_satellaview` must run before `wait_mcu_ready`.
6. **Check clear_wram runs early**: WRAM must be initialized before `setup_gfx`.

When MCU communication fails (menu hangs, "Loading..." forever):

7. **Check WRAM_WAIT_MCU routine**: Must be an infinite loop (no timeout). MCU operations take variable time.
8. **Check processor state preservation**: WRAM routines must `php`/`plp` to preserve caller's register widths.
9. **Check for emulator vs hardware**: In emulator, SNES_CMD never becomes $55 (no MCU). Emulator detection must timeout gracefully.
