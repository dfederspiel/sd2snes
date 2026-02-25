---
name: deploy
description: Build the SNES menu ROM then deploy m3nu.bin to the FXPAK Pro SD card. Backs up the existing file first.
disable-model-invocation: true
allowed-tools: Bash
argument-hint: "[drive-letter]"
---

# Build and Deploy to FXPAK Pro

Build the menu ROM and copy it to the sd2snes SD card for testing on real hardware.

## Steps

1. Build the ROM:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes && make 2>&1"
   ```

2. Check for build errors. If the build fails, stop and report.

3. Determine the target drive:
   - If an argument is provided (e.g., `/deploy G`), use that drive letter
   - Otherwise default to `F:`

4. Verify the target exists:
   ```
   ls "<DRIVE>:\sd2snes\"
   ```
   If the directory doesn't exist, tell the user to insert the SD card.

5. Back up the existing file:
   ```
   cp "<DRIVE>:\sd2snes\m3nu.bin" "<DRIVE>:\sd2snes\m3nu.bin.bak"
   ```

6. Copy the new ROM:
   ```
   cp "C:\Users\david\code\sd2snes\.claude\worktrees\vigorous-vaughan\snes\m3nu.bin" "<DRIVE>:\sd2snes\m3nu.bin"
   ```

7. Verify the copy (file size should be 65536 bytes).

8. Remind the user:
   - **Power cycle the FXPAK Pro** (turn SNES off then on). MCU loads menu ROM from SD on every boot.
   - Emulator-mode code won't activate on hardware (MCU responds with $55).
   - Palette and HDMA gradient changes ARE visible on hardware.
   - Backup is at `m3nu.bin.bak` if rollback is needed.
