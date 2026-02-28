# sd2snes / FXPAK Pro

SD card based multi-purpose cartridge for the Super Nintendo, originally created by [ikari_01](https://sd2snes.de/).

The sd2snes (now sold as FXPAK Pro) lets you load ROM files from an SD card and play them on real SNES hardware. It supports nearly the entire SNES library through FPGA-based enhancement chip emulation.

## Architecture

The cartridge has three main components:

| Component | Language | Directory | Description |
|-----------|----------|-----------|-------------|
| **SNES Menu ROM** | 65816 Assembly | `snes/`, `snes-64tass/` | The file browser UI that runs on the SNES itself |
| **MCU Firmware** | C (ARM Cortex-M3) | `src/` | Handles SD card I/O, file management, and SNES communication |
| **FPGA** | Verilog | `verilog/` | Cartridge bus interface and enhancement chip emulation |

## 64tass Port

The menu ROM is being ported from snescom to [64tass](http://tass64.sourceforge.net/), a modern and actively maintained 65816 assembler. The port lives in `snes-64tass/` alongside the original `snes/`.

**Why port?** snescom (by Bisqwit, circa 2005) works but has limitations that make development harder than it needs to be:
- No scoping — all labels are global, leading to naming collisions
- No structs, enums, or user-defined types
- Limited macro system
- No data bank or direct page tracking (the assembler can't catch addressing mode mistakes)
- No longer maintained

64tass provides scoping, `.databank`/`.dpage` validation, macros, structs, conditional assembly, and thorough error checking — catching real bugs that snescom silently accepts.

**Status**: 18 of 24 source files ported. The file browser, menu system, game launching, SPC player, and warm boot all work on real FXPAK Pro hardware. The remaining files are mostly large data blobs (logo graphics, save states) and the NMI hook.

**Goal**: Full feature parity with the snescom build, then use 64tass as the primary assembler going forward.

## Building

See `src/README` for full build instructions. Quick start:

```bash
# Menu ROM — snescom (original, requires snescom 1.8.1.1)
cd snes && make

# Menu ROM — 64tass (port in progress, requires 64tass)
cd snes-64tass && make

# MCU Firmware (requires arm-none-eabi-gcc)
cd src && make CONFIG=config-mk3
```

The FPGA mini bootstrap bitstream (`verilog/sd2snes_mini/fpga_mini.bi3`) is included as a pre-built binary extracted from the official v1.11.0 release, so you can build firmware without FPGA synthesis tools.

## Hardware Variants

| Variant | MCU | FPGA | Firmware |
|---------|-----|------|----------|
| sd2snes Mk.II | LPC1754 | Xilinx Spartan-3 | `firmware.im2` |
| sd2snes Mk.III / FXPAK Pro | LPC1756 | Intel Cyclone IV E | `firmware.im3` |

## Links

- [Official site](https://sd2snes.de/) - Downloads, documentation, and purchase info
- [Save States](README.Savestates.FURiOUS.md) - FURiOUS's save state implementation
