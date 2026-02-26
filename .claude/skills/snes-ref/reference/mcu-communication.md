# SNES ROM ↔ MCU Communication via FPGA

The sd2snes has three processors that must cooperate: the **SNES CPU** (65816), the **MCU** (ARM Cortex-M3/M4), and the **FPGA** (cartridge bus logic). They communicate through shared memory regions that the FPGA maps into the SNES address space.

## Architecture Overview

```
+----------+     SNES Bus     +----------+     SPI     +----------+
| SNES CPU | <--------------> |   FPGA   | <---------> |   MCU    |
| (65816)  |   $002Axx R/W    | (bridge) |  snescmd_*  | (ARM C)  |
+----------+                  +----------+             +----------+
                                   |
                              +----------+
                              |   SRAM   |  $C00000-$FFFFFF
                              | (SD card |  (ROM image, config,
                              |  data)   |   directory listings)
                              +----------+
```

The FPGA exposes two shared memory regions:
1. **BRAM (Block RAM)** at `$002A00-$002CFF` — fast FPGA-internal RAM, accessible by both SNES and MCU
2. **SRAM** at `$C00000-$FFFFFF` — large external RAM, holds ROM image, config, directory data

## BRAM: The Command Channel ($002A00-$002CFF)

BRAM is the primary communication mechanism between SNES and MCU. The FPGA maps it into SNES address space at `$002A00`. The MCU accesses it via SPI commands (`FPGA_CMD_SNESCMD_SETADDR`, `_READ`, `_WRITE`).

### Command Registers

| SNES Address | MCU Name | Size | Direction | Purpose |
|-------------|----------|------|-----------|---------|
| `$002A00` | `SNESCMD_MCU_CMD` | 1 byte | SNES → MCU | SNES writes command byte here |
| `$002A02` | `SNESCMD_SNES_CMD` | 1 byte | MCU → SNES | MCU writes status/ACK here |
| `$002A04` | `SNESCMD_MCU_PARAM` | 8 bytes | Bidirectional | Command parameters |

### Command Protocol (Menu Mode)

```
SNES (menu ROM)                    MCU (ARM firmware)

  boot → wait_mcu_ready            main() → load menu.bin from SD
  polls SNES_CMD for $55           → snes_set_snes_cmd(0x55)  [MCU_CMD_RDY]
  SNES_CMD == $55 ← ─ ─ ─ ─ ─ ─ ─ ─ ┘
  → filesel_init / fileselloop     → menu_main_loop() [polls MCU_CMD every 20ms]

  User selects a ROM:
  sta MCU_CMD [$01=LOADROM]  ─ ─ → reads MCU_CMD, dispatches cmd
  echo_mcu_cmd echoes $01 → SNES_CMD
  (SNES ignores this echo)

  Meanwhile in game_handshake:
  polls SNES_CMD for $55
                                   load_rom(): loads ROM to SRAM
                                   snes_set_snes_cmd(0x55) [ACK]
  SNES_CMD == $55 ← ─ ─ ─ ─ ─ ─ ─ ─ ┘
  sta MCU_CMD [$55]
  sta MCU_CMD [$0B=FPGA_RECONF]─ → waits for CMD_FPGA_RECONF
                                   reconfigures FPGA
                                   snes_set_snes_cmd(0x77)
  SNES_CMD == $77 ← ─ ─ ─ ─ ─ ─ ─ ─ ┘
  → copies fadeloop to BRAM
  → fadeloop: fade screen, fill
    WRAM, CMD_RESET  ─ ─ ─ ─ ─ ─ → waits for CMD_RESET ($80)
                                   → set_mapper() → assert_reset()
                                   → init(filename)  [installs nmihook!]
                                   → deassert_reset()
                                   → game boots
```

### Key Command Values

| Value | SNES Constant | MCU Constant | Meaning |
|-------|--------------|--------------|---------|
| `$01` | `CMD_LOADROM` | `SNES_CMD_LOADROM` | Load and launch a ROM |
| `$02` | `CMD_SETRTC` | `SNES_CMD_SETRTC` | Set RTC from SNES time data |
| `$0A` | `CMD_READDIR` | `SNES_CMD_READDIR` | Read directory listing to SRAM |
| `$0B` | `CMD_FPGA_RECONF` | `SNES_CMD_FPGA_RECONF` | Reconfigure FPGA for game mapper |
| `$55` | `CMD_MCU_RDY` | `MCU_CMD_RDY` | MCU is ready / ACK |
| `$77` | — | — | FPGA reconfig complete signal |
| `$80` | `CMD_RESET` | `SNES_CMD_RESET` | SNES requests reset |
| `$89` | `CMD_RESET_LOOP_PASS` | `SNES_CMD_RESET_LOOP_PASS` | Reset hook timing check passed |
| `$AA` | — | `MCU_CMD_ERR` | MCU error response |

### The $55 Trap

The MCU writes `$55` to SNES_CMD at **two different points**:
1. **Boot ready signal** — `main.c:286`: `snescmd_writebyte(MCU_CMD_RDY, SNESCMD_SNES_CMD)` — tells the menu ROM the MCU is alive
2. **LOADROM ACK** — `memory.c:300`: `snes_set_snes_cmd(0x55)` — inside `load_rom()` when `LOADROM_WAIT_SNES` flag is set

The SNES side (`game_handshake`) polls for `$55` as the ACK. It does NOT get $55 from `echo_mcu_cmd()` — that echoes the command byte ($01) back, which the SNES ignores while polling.

## BRAM: The NMI Hook System ($002A10-$002AFF)

This is the **most critical** and **least obvious** piece of the sd2snes architecture. After a game loads, the FPGA intercepts the game's NMI vector and redirects it to code stored in BRAM. This code provides:
- In-game button combos (reset to menu, enable/disable cheats)
- WRAM cheat patching
- Savestate support
- Joypad reading (auto-joypad or manual)

### How the NMI Hook Gets Installed

**Source**: The menu ROM (`nmihook.a65`) contains ~240 bytes of NMI/reset hook code. In the original snescom build, the linker places this at some address (e.g., `$C09A0E`).

**Pointer at $C0FF00**: The ROM header at `$C0FF00` contains a 16-bit word pointing to the hook code within the ROM:
```asm
; header.a65 (64tass port)
* = $C0FF00
nmihook_ptr
  .word nmihook & $ffff    ; e.g., $9A0E → MCU reads from $C09A0E in SRAM
```

**MCU reads the pointer**: During `init()` (called after SNES reset, before deassert_reset):
```c
// snes.c:587-593
void snescmd_prepare_nmihook() {
  uint16_t bram_src = sram_readshort(SRAM_MENU_ADDR + MENU_ADDR_BRAM_SRC);
  // SRAM_MENU_ADDR = $C00000, MENU_ADDR_BRAM_SRC = $FF00
  // So this reads 2 bytes from $C0FF00 in SRAM = the nmihook_ptr value
  uint8_t bram[BRAM_SIZE];  // BRAM_SIZE = 240
  sram_readblock(bram, SRAM_MENU_ADDR + bram_src, BRAM_SIZE);
  // Reads 240 bytes starting at SRAM_MENU_ADDR + bram_src
  snescmd_writeblock(bram, SNESCMD_INGAME_HOOK, BRAM_SIZE);
  // Writes to BRAM at $2A10 (SNESCMD_INGAME_HOOK)
}
```

**BRAM_SIZE** = 256 - (0x2A10 - 0x2A00) = **240 bytes**. This covers $2A10 through $2AFF.

**FPGA patches branches**: The hook code contains `bra` instructions at fixed byte offsets that the FPGA patches at runtime based on feature flags (cheats enabled, button combo state, etc.). The byte positions are hardcoded in the FPGA verilog.

### BRAM Memory Map During Gameplay

| SNES Address | MCU Name | Purpose |
|-------------|----------|---------|
| `$002A10` | `SNESCMD_INGAME_HOOK` | NMI hook entry point (FPGA redirects NMI here) |
| `$002A7D` | `SNESCMD_RESET_HOOK` | Reset hook (timing verification + `jmp ($fffc)`) |
| `$002AD8` | `SNESCMD_WRAM_CHEATS` | WRAM cheat patch code (programmed by MCU) |
| `$002BA0` | `SNESCMD_NMI_RESET` | Reset command word |
| `$002BF0` | `NMI_PAD` | Joypad state (read by hook) |
| `$002BF2` | `NMI_CMD` | NMI command (button combo → command mapping) |
| `$002BFC` | `NMI_BUTTONS_ENABLE` | Button enable flag |
| `$002BFD` | `NMI_VECT_DISABLE` | Write here to return to game's real NMI |
| `$002BFE` | `NMI_WRAM_PATCH_DISABLE` | WRAM patch enable/disable |
| `$002BFF` | `NMI_WRAM_PATCH_COUNT` | Number of active WRAM cheats |
| `$002C00` | `SNESCMD_EXE` | Executable code area (MCU can inject code here) |

### NMI Hook Execution Flow

When a game's NMI fires:
1. FPGA intercepts the NMI vector and redirects to `$002A10`
2. Hook saves processor state, reads `$4218` (joypad)
3. FPGA-controlled branch #1: skip to exit if buttons disabled or manual read in progress
4. If buttons enabled: check for button combos → map to NMI_CMD
5. Echo NMI_CMD to MCU_CMD (MCU can react to button combos)
6. FPGA-controlled branch #2: decide cheats/savestate/stop/exit
7. If cheats enabled: `jsr NMI_WRAM_CHEATS` ($2AD8) — MCU-programmed cheat code
8. If savestate: `jsl savestate_handler`
9. Exit: restore state, `jmp ($FF77)` — FPGA patches this vector to point to game's real NMI handler

### The nmihook Binary Blob

In our 64tass port, we cannot reassemble nmihook.a65 directly because:
1. The FPGA patches branch instructions at **fixed byte offsets** within the 240-byte block
2. Any change in code size/layout would misalign the FPGA's hardcoded patch positions
3. The hook contains `jsl savestate_handler` pointing to a specific ROM address in the original build

**Solution**: Extract the 240 bytes from the original snescom-built `menu.bin` at the offset indicated by the nmihook_ptr, and include them as a binary blob:
```asm
; main.a65
nmihook
  .binary "nmihook.bin"    ; 240 bytes, byte-exact from original ROM
```

**Verification**: The pointer at $C0FF00 must be `nmihook & $ffff`. If this points to wrong data, every game crashes on first NMI.

## SRAM: Shared Data Regions

The FPGA maps SRAM into the SNES address space. Both the MCU and SNES can access it (the MCU via SPI, the SNES via the cartridge bus).

### Key SRAM Regions

| SRAM Address | MCU Define | SNES Access | Purpose |
|-------------|-----------|-------------|---------|
| `$C00000` | `SRAM_MENU_ADDR` | Bank $C0 | Menu ROM image (64KB) |
| `$C10000` | `SRAM_DIR_ADDR` | `ROOT_DIR` | Directory listing from MCU |
| `$FF0000` | `SRAM_MENU_FILEPATH_ADDR` | `FILESEL_CWD` | Current working directory path |
| `$FF0100` | `SRAM_MENU_CFG_ADDR` | `CFG_ADDR` | Configuration block |
| `$FF1000` | `SRAM_CMD_ADDR` | — | Boot print message area |
| `$FF1100` | `SRAM_MCU_STATUS_ADDR` | `ST_MCU_ADDR` | MCU → SNES status (RTC valid, etc.) |
| `$FF1110` | `SRAM_SNES_STATUS_ADDR` | `ST_SNES_ADDR` | SNES → MCU status (Ultra16, Satellaview) |
| `$FF1200` | `SRAM_SYSINFO_ADDR` | `SYSINFO_BLK` | System information block |
| `$FF1420` | `SRAM_LASTGAME_ADDR` | `LAST_GAME` | Last game filename |

### SNES → MCU Data Flow via SRAM

The SNES writes data to SRAM that the MCU reads later:

1. **File selection**: `select_file` in filesel.a65 writes the CWD path to `MCU_PARAM` ($2A04) and the selected filename pointer to `MCU_CMD+$08` ($2A08). The MCU's `get_selected_name()` reads these via BRAM and reconstructs the full path from SRAM.

2. **Hardware detection**: `detect_ultra16` and `detect_satellaview` (run at boot) write status flags to SRAM:
   ```
   $FF1110 (ST_IS_U16)          — 1 if Ultra16 detected
   $FF1111 (ST_U16_CFG)         — Ultra16 config byte
   $FF1112 (ST_HAS_SATELLAVIEW) — 1 if Satellaview base unit present
   ```
   The MCU reads these via `status_save_from_menu()` → `STS` struct. This affects:
   - Reset pulse duration: Ultra16 needs 60x longer reset (300ms vs 5ms)
   - Satellaview base emulation: disabled if real hardware detected

3. **Configuration**: Settings written to `CFG_ADDR` ($FF0100) are saved by MCU via `CMD_SAVE_CFG`.

### MCU → SNES Data Flow via SRAM

1. **Directory listings**: MCU reads SD card directories and writes them to `$C10000` (`ROOT_DIR`). Format: 23-byte entries (type byte + padded filename). SNES reads these to populate the file browser.

2. **MCU status**: MCU writes to `$FF1100` (`ST_MCU_ADDR`):
   ```
   $FF1100 (ST_RTC_VALID)         — 1 if RTC has valid time
   $FF1101 (ST_NUM_RECENT_GAMES)  — count of recent games
   $FF1102 (ST_PAIRMODE)          — pair mode state
   $FF1103 (ST_NUM_FAVORITE_GAMES)— count of favorites
   ```

3. **Configuration**: MCU writes saved config to `$FF0100` before signaling ready.

## BRAM During Game Launch (Temporary Use)

During the game launch sequence, BRAM is temporarily repurposed:

1. **Before launch**: BRAM contains the menu's communication registers (MCU_CMD, SNES_CMD, etc.)
2. **game_handshake**: SNES sends CMD_LOADROM, waits for $55 ACK, sends CMD_FPGA_RECONF
3. **After FPGA reconfig ($77 signal)**: SNES copies `fadeloop` routine from WRAM to BRAM ($002A10)
4. **fadeloop executes from BRAM**: Fades screen, fills WRAM with $55, sends CMD_RESET
5. **MCU receives CMD_RESET**: Calls `assert_reset() → init() → deassert_reset()`
6. **init() overwrites BRAM**: `snescmd_prepare_nmihook()` copies the NMI hook code to BRAM, **replacing the fadeloop**
7. **Game boots**: FPGA redirects game NMI to the hook code now in BRAM

This is why the fadeloop must be small enough to fit in BRAM, and why nmihook overwrites it — they share the same address space but are never needed simultaneously.

## Debugging Checklist

When game launching fails (black screen after file selection):

1. **Check nmihook_ptr at $C0FF00**: Must be a valid 16-bit offset into the ROM. Read 2 bytes at ROM offset $3F00 (since $C0FF00 - $C0C000 = $3F00 in a 64KB HiROM). Zero = broken.

2. **Verify nmihook data at the pointed offset**: The 240 bytes must be actual 65816 hook code, not zeros or unrelated code. Compare against known-good original ROM.

3. **Check fadeloop copies correctly**: `store_blockram_routine` copies fadeloop to BRAM after FPGA reconfig. Verify the MVN operands are correct (64tass reverses src/dst vs snescom).

4. **Check WRAM routines are present**: `store_wram_routines` must have correct DMA7 sizes. If the copy is too short, the `rtl` at the end isn't copied → execution runs into garbage.

5. **Check SRAM status flags**: `detect_ultra16` and `detect_satellaview` must run before `wait_mcu_ready`. Missing = garbage in STS flags = wrong reset timing.

6. **Check clear_wram runs early**: WRAM must be initialized before `setup_gfx` (which sets `window_stack_head = $FFFF`). Without this, `push_window` in filesel corrupts WRAM routines.

## Critical Lesson: The ROM Binary Is an API

The menu ROM is not just SNES code — it's also a **data source** that the MCU reads from. The MCU treats specific ROM offsets as structured data:

| ROM Offset | MCU Reads | What It Expects |
|-----------|-----------|-----------------|
| `$C0FF00` | `snescmd_prepare_nmihook()` | 16-bit pointer to 240 bytes of NMI hook code |
| `$FF0000` | `get_selected_name()` (via BRAM param) | Null-terminated CWD path string |
| `$FF0100` | config system | Configuration structure |
| `$FF1110` | `status_save_from_menu()` | 3-byte snes_status_t (Ultra16, Satellaview flags) |

If ANY of these offsets contain wrong data, the MCU will silently use garbage values. There are no checksums or validation — the MCU trusts the ROM binary completely.

**When porting the ROM**: Every byte of the binary matters, not just the SNES-executable code. Data structures, pointers, and binary blobs that the MCU reads must be preserved exactly. A missing `.word` at `$C0FF00` can cause every game to crash even though the menu ROM itself works perfectly.
