# sd2snes / FXPAK Pro

SD card based multi-purpose cartridge for the Super Nintendo, originally created by [ikari_01](https://sd2snes.de/).

The sd2snes (now sold as FXPAK Pro) lets you load ROM files from an SD card and play them on real SNES hardware. It supports nearly the entire SNES library through FPGA-based enhancement chip emulation.

## Architecture

The cartridge has three main components:

| Component | Language | Directory | Description |
|-----------|----------|-----------|-------------|
| **SNES Menu ROM** | 65816 Assembly | `snes/` | The file browser UI that runs on the SNES itself |
| **MCU Firmware** | C (ARM Cortex-M3) | `src/` | Handles SD card I/O, file management, and SNES communication |
| **FPGA** | Verilog | `verilog/` | Cartridge bus interface and enhancement chip emulation |

## Building

See `src/README` for full build instructions. Quick start for the menu ROM:

```bash
# Menu ROM (requires snescom 1.8.1.1)
cd snes && make

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
