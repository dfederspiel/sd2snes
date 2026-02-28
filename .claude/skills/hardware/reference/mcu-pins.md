# LPC1756 Pin Map — FXPAK Pro (Mk.III)

## MCU Overview
- **Chip**: NXP LPC1756 (ARM Cortex-M3)
- **Package**: LQFP80 (20 pins per side, QFP with solderable legs)
- **Clock**: 96 MHz (8 MHz xtal x24 /4)
- **Flash**: 256 KB, **SRAM**: 32 KB

## LQFP80 Package Constraints

Not all GPIO ports are bonded out. Pins **not available** on LQFP80:
- Port 0: P0.12, P0.13, P0.14, P0.31
- Port 1: P1.2, P1.3, P1.5, P1.6, P1.7, P1.11, P1.12, P1.13
- Port 3: Only P3.25 and P3.26 exist (rest absent)
- Port 4: Only P4.28 and P4.29 exist

## Pins Used by Mk.III Firmware

Source: `src/config-mk3` (CONFIG defines) and `src/bootldr/main.c` (PINSEL setup).

### SD Card Interface
| Pin | Function | Direction | Config define |
|-----|----------|-----------|---------------|
| P0.7 | SD_CLK | Out | SD_CLKREG=LPC_GPIO0, SD_CLKBIT=7 |
| P0.8 | SD_DT (card detect) | In | SD_DTREG=LPC_GPIO0, SD_DTBIT=8 |
| P0.9 | SD_CMD | I/O | SD_CMDREG=LPC_GPIO0, SD_CMDBIT=9 |
| P2.0 | SD_DAT0 | I/O | SD_DAT0REG=LPC_GPIO2, SD_DAT0BIT=0 |
| P2.1 | SD_DAT1 | I/O | SD_DAT1REG=LPC_GPIO2, SD_DAT1BIT=1 |
| P2.2 | SD_DAT2 | I/O | SD_DAT2REG=LPC_GPIO2, SD_DAT2BIT=2 |
| P2.3 | SD_DAT3 | I/O | SD_DAT3REG=LPC_GPIO2, SD_DAT3BIT=3 |

### SPI Bus (SSP0) — SD Card + FPGA
| Pin | Function | Direction | Mux |
|-----|----------|-----------|-----|
| P0.15 | SSP0 SCK | Out | PINSEL AF2 |
| P0.16 | SSP0 SSEL (FPGA CS) | Out | GPIO (manual) |
| P0.17 | SSP0 MISO | In | PINSEL AF2 |
| P0.18 | SSP0 MOSI | Out | PINSEL AF2 |

### FPGA Configuration
| Pin | Function | Direction | Config define |
|-----|----------|-----------|---------------|
| P4.28 | FPGA_CCLK | Out | FPGA_CCLKREG=LPC_GPIO4, FPGA_CCLKBIT=28 |
| P4.29 | FPGA_PROGB | Out | FPGA_PROGBREG=LPC_GPIO4, FPGA_PROGBBIT=29 |
| P2.9 | FPGA_INITB | In | FPGA_INITBREG=LPC_GPIO2, FPGA_INITBBIT=9 |
| P2.8 | FPGA_DIN | Out | FPGA_DINREG=LPC_GPIO2, FPGA_DINBIT=8 |
| P0.22 | FPGA_DONE | In | FPGA_DONEREG=LPC_GPIO0, FPGA_DONEBIT=22 |
| P0.11 | FPGA_CLK (MAT3.1) | Out | Timer 3 match output |

Note: P4.28/P4.29 are shared with UART3 via PINSEL muxing. After FPGA config, they switch to UART3 TX/RX.

### UART3 (Debug Serial) — 115200 baud
| Pin | Function | Mux |
|-----|----------|-----|
| P0.25 | TXD3 | PINSEL AF3 (set in bootldr/main.c) |
| P0.26 | RXD3 | PINSEL AF3 (set in bootldr/main.c) |

Source: `bootldr/main.c` line 34-35:
```c
/* connect UART3 on P0[25:26] + SSP0 on P0[15:18] + MAT3.0 on P0[10] */
LPC_PINCON->PINSEL1 = BV(18) | BV(19) | BV(20) | BV(21) /* UART3 */
```

### SNES Interface
| Pin | Function | Direction | Config define |
|-----|----------|-----------|---------------|
| P1.4 | SNES_RESET | Out | SNES_RESETREG=LPC_GPIO1, SNES_RESETBIT=4 |
| P1.8 | SNES_CIC_D0 | I/O | SNES_CIC_D0REG=LPC_GPIO1, SNES_CIC_D0BIT=8 |
| P1.9 | SNES_CIC_D1 | I/O | SNES_CIC_D1REG=LPC_GPIO1, SNES_CIC_D1BIT=9 |
| P1.10 | SNES_CIC_STATUS | In | SNES_CIC_STATUSREG=LPC_GPIO1, SNES_CIC_STATUSBIT=10 |
| P1.14 | SNES_CIC_PAIR | Out | SNES_CIC_PAIRREG=LPC_GPIO1, SNES_CIC_PAIRBIT=14 |

### LEDs (PWM via Timer 0)
| Pin | Function | Color | PWM channel |
|-----|----------|-------|-------------|
| P1.20 | LED_WRITE | Red | PWM1[2] (AF2) |
| P1.23 | LED_READ | Yellow | PWM1[4] (AF2) |
| P1.24 | LED_READY | Green | PWM1[5] (AF2) |

### USB
| Pin | Function | Mux |
|-----|----------|-----|
| P0.29 | USB D+ | AF1 |
| P0.30 | USB D- | AF1 |
| P1.18 | USB_CONN | GPIO out |
| P1.30 | USB_VBUS | GPIO in (pull-up) |

### Audio DAC
| Pin | Function | Direction |
|-----|----------|-----------|
| P1.1 | DAC_DEM | Out |

### Hardware Revision Detection (HWREV0-7)
| Bit | Pin | Pull |
|-----|-----|------|
| HWREV0 | P1.31 (phys 17) | Up | ⚠️ **On P401 pos 14** |
| HWREV1 | P2.4 | Up |
| HWREV2 | P2.6 | Up |
| HWREV3 | P1.15 | Up |
| HWREV4 | P1.28 | Down |
| HWREV5 | P2.7 | Down |
| HWREV6 | P0.10 | Down |
| HWREV7 | P2.5 | Down |

Revision encoding (`src/hwinfo.c`): `id = (HWREV7..HWREV0) XOR 0x0f`
- Maker: >= 0xB0 = KRIKzz, <= 0x40 = ikari_01
- Model: `(id - maker_base) >> 4` (0=sd2snes, 1=FXPAK Pro)
- Revision: `(id - maker_base) & 0x0F` → letter 'A' + rev - 1

## Non-GPIO Pins on P401 Header

These dedicated pins are broken out on the P401 header but are not GPIO:

| Phys | Function | P401 pos | Notes |
|------|----------|----------|-------|
| 1 | TDO / SWO | 9 | JTAG test data out / SWD serial wire output |
| 2 | TDI | 2 | JTAG test data in |
| 3 | TMS / SWDIO | 10 | JTAG test mode select / SWD data |
| 4 | TRST | 3 | JTAG reset (active low) |
| 5 | TCK / SWDCLK | 11 | JTAG test clock / SWD clock |
| 14 | RESET | 5 | System reset (has pullup to VDD) |
| 16 | VDD (3.3V) | 13 | Digital power supply |

## Free Pins (available on LQFP80, not used by Mk.III firmware)

### Port 0 — Best expansion candidates
| Pin | Phys | Notable alt functions | Notes |
|-----|------|----------------------|-------|
| P0.0 | 37 | UART3 RX (alt), I2C1 SDA, CAN1 RX | Was CIC_D1 on Mk.II, free on Mk.III |
| P0.1 | 38 | UART3 TX (alt), I2C1 SCL, CAN1 TX | Was CIC_D0 on Mk.II, free on Mk.III |
| P0.2 | 79 | **UART0 TX (TXD0)**, AD0[7] | **P401 pos 8** — no soldering needed |
| P0.3 | 80 | **UART0 RX (RXD0)**, AD0[6] | **P401 pos 1** — no soldering needed |
| P0.4 | — | I2C1 SDA (alt), GPIO | |
| P0.5 | — | I2C1 SCL (alt), GPIO | |
| P0.6 | — | I2S, SSP1 SSEL | Was SD_WP on Mk.II, free on Mk.III |
| P0.19 | — | I2C1 SDA, USB_CONNECT | |
| P0.20 | — | I2C1 SCL, USB_PWRD | |
| P0.21 | — | GPIO | |
| P0.23 | — | GPIO, AD0.0 | ADC capable |
| P0.24 | — | GPIO, AD0.1 | ADC capable |
| P0.25 | 7 | **UART3 TXD** | Debug serial (firmware uses). **P401 pos 12** |
| P0.26 | 6 | **UART3 RXD** | Debug serial (firmware uses). **P401 pos 4** |
| P0.27 | — | **I2C0 SDA** | Dedicated I2C (open-drain, no GPIO mode) |
| P0.28 | — | **I2C0 SCL** | Dedicated I2C (open-drain, no GPIO mode) |

### Port 1
| Pin | Notes |
|-----|-------|
| P1.0 | GPIO |
| P1.16 | GPIO |
| P1.17 | GPIO |
| P1.19 | GPIO (was HWREV1 on Mk.II) |
| P1.22 | GPIO (was HWREV3 on Mk.II) |
| P1.25 | GPIO |
| P1.26 | GPIO (was SNES_RESET on Mk.II) |
| P1.27 | GPIO |
| P1.29 | GPIO |

### Port 2
| Pin | Notes |
|-----|-------|
| P2.10 | GPIO, EINT0 |
| P2.11 | GPIO, EINT1 |
| P2.12 | GPIO, EINT2 |
| P2.13 | GPIO, EINT3 |

### Port 3
| Pin | Notes |
|-----|-------|
| P3.25 | GPIO, MAT0.0 | Only 2 Port 3 pins on LQFP80 |
| P3.26 | GPIO, MAT0.1 | |

**Total free: ~25-30 pins** (exact count depends on which are actually routed on the PCB).

## Peripheral Availability for Expansion

| Peripheral | Status | Best pins | Speed |
|------------|--------|-----------|-------|
| **UART0** | Free | P0.2/TXD0 (TX), P0.3/RXD0 (RX) — **on P401** | Up to 6 Mbaud |
| **SSP1** (SPI) | Free but pin conflicts | See note below | Up to 48 MHz |
| **I2C0** | Free | P0.27 (SDA), P0.28 (SCL) | 400 kHz |
| **I2C1** | Free | P0.0/P0.19 (SDA), P0.1/P0.20 (SCL) | 400 kHz |
| **CAN1** | Free | P0.0 (RD1), P0.1 (TD1) | 1 Mbps |
| **ADC** | Free | P0.23-P0.26 | 200 kHz 12-bit |

**SSP1 note**: Default SSP1 pins (P0.7-P0.9) conflict with SD card. Alternative pins:
- SCK: P1.31 (AF2) — conflicts with HWREV0
- SSEL: P0.6 (AF2) — free on Mk.III
- MISO: P1.18 (AF3) — conflicts with USB_CONN
- MOSI: P1.22 (AF3) — free on Mk.III
Bit-bang SPI on free GPIO is more practical than working around SSP1 conflicts.

## Expansion Recommendations

### For ESP32 sidecar (networking)
**UART0 via P401 header (simplest, 3 wires, no MCU soldering)**:
- P401 pos 8 → P0.2/TXD0 (MCU pin 79) → connect to ESP32 RX
- P401 pos 1 → P0.3/RXD0 (MCU pin 80) → connect to ESP32 TX
- P401 pos 6 → GND → connect to ESP32 GND
- Hardware UART0, DMA-capable, existing driver infrastructure in firmware
- 921600 baud = ~100 KB/s, sufficient for file transfers

**SPI bit-bang approach (faster, 5 wires)**:
- Pick any 4 free GPIO (e.g., P0.2-P0.5) + GND
- 96 MHz MCU can bit-bang several Mbps
- Better for bulk ROM downloads

**I2C approach (fewest wires, slowest)**:
- P0.27 (I2C0 SDA) + P0.28 (I2C0 SCL) + GND
- Hardware I2C with open-drain, 2 wires + ground
- 400 kHz max — too slow for ROM transfers, fine for commands

### Firmware integration path
- UART driver already exists (`src/lpc175x/uart.c`) — change CONFIG_UART_NUM or add second UART
- Add `src/network.c` for ESP32 command protocol
- MCU downloads files to SD card; menu ROM sees them as normal files
