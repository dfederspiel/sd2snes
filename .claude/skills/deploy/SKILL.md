---
name: deploy
description: Build and deploy menu ROM and/or MCU firmware to the FXPAK Pro SD card. Backs up existing files first.
disable-model-invocation: true
argument-hint: "[firmware] [drive-letter]"
---

# Build and Deploy to FXPAK Pro

Build and copy files to the sd2snes SD card for testing on real hardware.

## Target Selection

- **No argument**: Build and deploy menu ROM only (`m3nu.bin`)
- **"firmware"**: Build and deploy MCU firmware only (`firmware.im3`)
- **"all"**: Build and deploy both

## Steps — Menu ROM (default)

1. Build the ROM:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes && make 2>&1"
   ```

2. Check for build errors. If the build fails, stop and report.

3. Determine the target drive:
   - If a drive letter argument is provided (e.g., `/deploy G`), use that
   - Otherwise default to `F:`

4. Verify the target exists:
   ```
   ls "<DRIVE>:/sd2snes/"
   ```
   If the directory doesn't exist, tell the user to insert the SD card.

5. Back up the existing file:
   ```
   cp "<DRIVE>:/sd2snes/m3nu.bin" "<DRIVE>:/sd2snes/m3nu.bin.bak"
   ```

6. Copy the new ROM:
   ```
   cp "C:/Users/david/code/sd2snes/.claude/worktrees/vigorous-vaughan/snes/m3nu.bin" "<DRIVE>:/sd2snes/m3nu.bin"
   ```

7. Verify the copy (file size should be 65536 bytes).

8. Remind the user:
   - **Power cycle the FXPAK Pro** (turn SNES off then on). MCU loads menu ROM from SD on every boot.
   - Emulator-mode code won't activate on hardware (MCU responds with $55).
   - Palette and HDMA gradient changes ARE visible on hardware.
   - Backup is at `m3nu.bin.bak` if rollback is needed.

## Steps — MCU Firmware

1. Build the firmware:
   ```
   wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/src && make CONFIG=config-mk3 2>&1"
   ```

2. Check for build errors. If the build fails, stop and report.

3. Determine the target drive (same as above, default `F:`).

4. Back up the existing firmware:
   ```
   cp "<DRIVE>:/sd2snes/firmware.im3" "<DRIVE>:/sd2snes/firmware.im3.bak"
   ```

5. Copy the new firmware:
   ```
   cp "C:/Users/david/code/sd2snes/src/obj-mk3/firmware.im3" "<DRIVE>:/sd2snes/firmware.im3"
   ```

6. Verify the copy (file size should be ~141KB).

7. Remind the user:
   - **Power cycle the FXPAK Pro**. The bootloader detects the new firmware and flashes it.
   - The bootloader is separate and always works — if the firmware is bad, restore `firmware.im3.bak`.
   - Stock backup from original v1.11.0 may also exist as `firmware.im3.stock-backup`.
