---
name: build
description: Build the SNES menu ROM. Supports both snescom (snes/) and 64tass (snes-64tass/) targets.
disable-model-invocation: true
argument-hint: "[64tass] [clean]"
---

# Build the SNES Menu ROM

Build the sd2snes SNES menu ROM. Supports two assembler targets.

## Target Selection

- **No argument** or **"clean"**: Build with snescom (default, `snes/` directory)
- **"64tass"** or **"64tass clean"**: Build with 64tass (`snes-64tass/` directory)

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
