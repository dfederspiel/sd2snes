---
name: test
description: Build the SNES menu ROM then launch it in bsnes-plus emulator for visual testing. Supports both snescom and 64tass targets.
disable-model-invocation: true
argument-hint: "[64tass]"
---

# Build and Test in Emulator

Build the menu ROM and launch it in bsnes-plus for visual verification.

## Target Selection

- **No argument**: Build and test snescom version (`snes/`)
- **"64tass"**: Build and test 64tass version (`snes-64tass/`)

## snescom Test (default)

1. Build the ROM:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes && make 2>&1"
   ```

2. Check for build errors. Ignore mkmap.sh error 127 and "Short jump out of range" warnings. If real errors occur, stop and report.

3. Check that `snes/menu.cht` is empty or absent. If it exists and is non-empty, warn: cheats can bypass emulator detection (especially `002a0255` which forces SNES_CMD=$55).

4. Launch bsnes-plus:
   ```
   start "" "C:\Users\david\tools\bsnes-plus\extracted\bsnes-accuracy.exe" "C:\Users\david\code\sd2snes\.claude\worktrees\vigorous-vaughan\snes\menu.bin"
   ```

5. Tell the user what to expect:
   - Emulator mode activates (MCU doesn't respond with $55)
   - Pink gradient background and emulator mode text should be visible
   - NMI handler maintains display at 60fps

## 64tass Test

1. Build the ROM:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes-64tass && make 2>&1"
   ```

2. Check for build errors. Any errors from 64tass are real (no harmless warnings to ignore). If errors, stop and report.

3. Verify `menu.xml` manifest exists in `snes-64tass/` (required for bsnes to detect HiROM on 64KB ROM).

4. Launch bsnes-plus:
   ```
   start "" "C:\Users\david\tools\bsnes-plus\extracted\bsnes-accuracy.exe" "C:\Users\david\code\sd2snes\.claude\worktrees\vigorous-vaughan\snes-64tass\menu.bin"
   ```

5. Tell the user what to expect based on current milestone:
   - **Milestone 1**: Solid dark blue/purple screen (backdrop color only, no BG layers)
   - **Milestone 2** (future): Pink gradient, text rendering via hiprint
   - **Milestone 3** (future): Full menu with file browser

## Emulator mode behavior (snescom)
Without sd2snes hardware, `wait_mcu_ready` times out after ~65536 polls, SNES_CMD != $55, so `emu_mode` runs. This renders text via hiprint then enters an infinite NMI-driven display loop.
