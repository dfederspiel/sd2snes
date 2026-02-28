---
name: build
description: Build the SNES menu ROM or MCU firmware. Supports snescom, 64tass, and MCU firmware targets.
disable-model-invocation: true
argument-hint: "[64tass] [firmware] [clean]"
---

# Build sd2snes Components

Build the sd2snes SNES menu ROM or MCU firmware.

## Target Selection

- **No argument** or **"clean"**: Build with snescom (default, `snes/` directory)
- **"64tass"** or **"64tass clean"**: Build with 64tass (`snes-64tass/` directory)
- **"firmware"** or **"firmware clean"**: Build MCU firmware (`src/` directory, config-mk3)

## snescom Build (default)

1. If "clean" is in the arguments, first remove build artifacts:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes && rm -f *.o65 menu.bin m3nu.bin header.ips"
   ```

2. Run the build:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes && make 2>&1"
   ```

3. Analyze the build output:
   - **Error 127 from `utils/mkmap.sh`**: Harmless (script not in worktree). Ignore.
   - **"Short jump out of range" warnings**: Pre-existing, non-fatal. Note but don't treat as errors.
   - **Any other errors**: Real failures. Report the failing file and line number.

4. Report results:
   - Success: confirm build succeeded, show file sizes for `menu.bin` and `m3nu.bin` (both should be exactly 65536 bytes).
   - Failure: show error(s), suggest which .a65 file to investigate.

### Known harmless output (snescom)
- `utils/mkmap.sh: not found` or exit code 127 from mkmap
- `Short jump out of range` warnings from snescom

## 64tass Build

1. If "clean" is in the arguments:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes-64tass && make clean"
   ```

2. Run the build:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes-64tass && make 2>&1"
   ```

3. Analyze the build output:
   - **"not a data bank address"**: Real error. The `.databank` directive doesn't match the actual DBR for the register being accessed. Check if DBR is correct at that point in code.
   - **"not defined symbol"**: Include order issue or missing constant in memmap.i65.
   - **"too large for a 16 bit unsigned integer"**: Label is 24-bit but used in a 16-bit context (e.g., vector table needs `& $ffff`).
   - **Zero errors**: Success.

4. Report results:
   - Success: confirm build succeeded, show file size for `menu.bin` (should be exactly 65536 bytes).
   - Failure: show error(s) with context about likely `.databank` or syntax issues.

## MCU Firmware Build

Builds the ARM Cortex-M3 MCU firmware for the FXPAK Pro (Mk.III).

### Prerequisites
- `arm-none-eabi-gcc` installed in WSL (`sudo apt install gcc-arm-none-eabi`)
- `src/utils/genhdr` built (`cd src/utils && make`)
- `utils/bin2c` built (`cd utils && gcc -o bin2c bin2c.c`)
- `verilog/sd2snes_mini/fpga_mini.bi3` present (54,754 bytes, extracted from stock firmware and checked into git)

### Build Steps

1. If "clean" is in the arguments:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/src && make CONFIG=config-mk3 clean"
   ```

2. Run the build:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/src && make CONFIG=config-mk3 2>&1"
   ```

3. Analyze the build output:
   - **`#define CONFIG_MK3_STM32 n`** in errors: CRLF line endings in config-mk3. Fix: `sed -i 's/\r$//' config-mk3`
   - **`region 'flash' overflowed`**: fpga_mini.bi3 is too large (wrong file used as stand-in)
   - **`utils/genhdr: not found`**: Build genhdr first (`cd src/utils && make`)
   - **`bin2c: not found`**: Build bin2c first (`cd utils && gcc -o bin2c bin2c.c`)

4. Report results:
   - Success: confirm `obj-mk3/firmware.im3` was produced, show file size (~141KB expected).
   - Failure: show error(s) and suggest fix.
