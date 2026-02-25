---
name: build
description: Clean build the SNES menu ROM via WSL make. Reports success/failure, warnings vs errors, and output file sizes.
disable-model-invocation: true
allowed-tools: Bash
argument-hint: "[clean]"
---

# Build the SNES Menu ROM

Build the sd2snes SNES menu ROM using the WSL-hosted snescom toolchain.

## Steps

1. If the argument is "clean", first remove build artifacts:
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
   - **Any other errors** (undefined symbol, syntax error, snescom/sneslink nonzero): Real failures. Report the failing file and line number.

4. Report results:
   - Success: confirm build succeeded, show file sizes for `menu.bin` and `m3nu.bin` (both should be exactly 65536 bytes).
   - Failure: show error(s), suggest which .a65 file to investigate.

## Known harmless output
- `utils/mkmap.sh: not found` or exit code 127 from mkmap
- `Short jump out of range` warnings from snescom
