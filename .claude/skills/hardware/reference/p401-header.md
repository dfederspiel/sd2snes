# P401 Expansion Header — FXPAK Pro Rev Z

## Physical Description
- **Label**: P401
- **Pins**: 14 unsoldered through-hole pads
- **Location**: Near MCU, traces pins wrapping around the bottom-left corner of the LQFP80
- **Board**: FXPAK Pro Rev Z (ikari_01)
- **Purpose**: Combined JTAG/SWD debug + UART + power header

## Status: FULLY MAPPED (continuity-tested 2026-02-28)

## Physical Layout

Orientation: cartridge slot on LEFT, board right edge on BOTTOM facing you.
2 rows x 7 pins. All pads outlined in white silkscreen. Square pad at top-right (pos 7).

```
Top row:     (1)  (2)  (3)  (4)  (5)     (6=GND)  [■7]
Bottom row:  (8)  (9)  (10) (11) (12)    (13)     (14)
              ↑ WEST (left)                  EAST (right) →
```

## Complete Pin Map

The header traces MCU pins wrapping counterclockwise around the LQFP80 bottom-left
corner. Top row = even MCU pins, bottom row = odd MCU pins, skipping crystal/power
pins in the 8-13 range.

| Pos | MCU Pin | GPIO / Function | Category | Notes |
|-----|---------|----------------|----------|-------|
| **1** | 80 | **P0.3 / RXD0** | UART0 RX | Also I2C1 SCL, AD0[6] |
| **2** | 2 | **TDI** | JTAG | |
| **3** | 4 | **TRST** | JTAG | Active-low JTAG reset |
| **4** | 6 | **P0.26 / RXD3** | UART3 RX | Debug serial (used by firmware) |
| **5** | 14 | **RESET** | System | Beeps to pin 16 (VDD) via pullup resistor |
| **6** | — | **GND** | Power | Confirmed continuity to ground plane |
| **7** | — | **VDD (3.3V)** | Power | Square pad. Confirmed 3.28V measured |
| **8** | 79 | **P0.2 / TXD0** | UART0 TX | Also I2C1 SDA, AD0[7] |
| **9** | 1 | **TDO / SWO** | JTAG/SWD | Serial wire output in SWD mode |
| **10** | 3 | **TMS / SWDIO** | JTAG/SWD | SWD data pin |
| **11** | 5 | **TCK / SWDCLK** | JTAG/SWD | SWD clock pin |
| **12** | 7 | **P0.25 / TXD3** | UART3 TX | Debug serial (used by firmware) |
| **13** | 16 | **VDD (3.3V)** | Power | Pairs with GND at pos 6 |
| **14** | 17 | **P1.31 / SCK1 / AD0[5]** | GPIO/ADC | ⚠️ Also HWREV0 — see warning below |

### MCU pins skipped by the header (pins 8-16 region)
| MCU Pin | Function | Why not broken out |
|---------|----------|--------------------|
| 8 | XTAL1 | Crystal oscillator input |
| 9 | XTAL2 | Crystal oscillator output |
| 10 | VSS | Ground (internal) |
| 11 | RTCX1 or RSTOUT | RTC crystal / reset output |
| 12 | RTCX2 or VDDA | RTC crystal / analog power |
| 13 | VSSA or RESET | Analog ground / reset |
| 15 | VBAT | Battery backup for RTC |

*Exact assignment of pins 10-15 depends on LPC1756 vs LPC1754 variant; the key point
is they're all crystal, power, or reset — none are GPIO.*

## Functional Groups

### UART0 — PROVEN WORKING with ESP32 sidecar (2026-03-01)
- **Pos 8** (P0.2/TXD0) → ESP32 GPIO4 (RX)
- **Pos 1** (P0.3/RXD0) ← ESP32 GPIO2 (TX)
- **Pos 6** (GND) → ESP32 GND
- ESP32 powered via its own USB cable (don't power from P401 VDD)
- **Baud**: 115200 8N1, DLL=13 (PCLK=24MHz = CCLK/4 default)
- Bidirectional PING/PONG verified. See [ESP32 Sidecar Reference](esp32-sidecar.md)

### JTAG — Full 5-pin JTAG interface
- **Pos 2** = TDI (test data in)
- **Pos 9** = TDO/SWO (test data out / serial wire output)
- **Pos 10** = TMS/SWDIO (test mode select / SWD data)
- **Pos 3** = TRST (JTAG reset, active low)
- **Pos 11** = TCK/SWDCLK (test clock / SWD clock)
- **Pos 5** = RESET (system reset)
- **Pos 6** = GND

### SWD — 2-wire debug (subset of JTAG pins)
- **Pos 10** = SWDIO (data)
- **Pos 11** = SWDCLK (clock)
- **Pos 5** = RESET (optional)
- **Pos 6** = GND
- **Pos 13** = VDD (target voltage reference)

### UART3 — Debug serial (921600 baud, 8N1)
- **Pos 4** = P0.26/RXD3 (receive)
- **Pos 12** = P0.25/TXD3 (transmit)
- Bootloader briefly uses 115200 (hardcoded divisor), then main firmware reinits at 921600
- Source: `src/config-mk3` line 66: `CONFIG_UART_BAUDRATE = 921600`
- Available for monitoring firmware debug output (see boot messages below)

### Power
- **Pos 6** = GND
- **Pos 7** = VDD (3.3V) — square pad, confirmed 3.28V
- **Pos 13** = VDD (3.3V)

## UART3 Boot Messages

On power-on, the firmware prints to UART3 (pos 12) at **921600 baud, 8N1**:

```
?                          ← bootloader init (briefly at 115200, then reinit to 921600)

sd2snes Mk.III +ESP32      ← main firmware banner (custom build)
===============
fw ver.: 1.11.1-esp32
cpu clock: 96000000 Hz
PCONP=a2a18248             ← bit 3 set = UART0 powered on
[ESP32] UART0 ready (115200 8N1, DLL=13)
card seems to be sending data, attempting deselect
CMD7 timed out
sd_init start
RCA: aaaa
...
(                          ← menu ROM load start
)                          ← menu ROM load complete
RTC valid!                 ← (or "RTC invalid!")
SNES GO!                   ← handoff to SNES
test sram
ok
[ESP32] Hello from ESP32: <N>
[ESP32] PONG seq=0         ← first successful PING/PONG
[ESP32] PONG seq=1
```

Source files: `src/main.c` (banner, ROM load, RTC, SNES GO), `src/esp32.c` (ESP32 lines),
`src/bootldr/uart.c` (`?`), `src/fpga.c` (FPGA config: `P`, `p`, `C`, `c`).

Additional output appears during file browser navigation (directory reads) and game loading.

**Reading UART3 without a USB-serial adapter**: An ESP32 with a free UART can tap this line.
Wire P401 pos 12 (TXD3) → ESP32 GPIO34 (input-only). Configure `Serial1.begin(921600, SERIAL_8N1, 34, -1)`.
Add INPUT_PULLUP on GPIO34 and filter non-printable bytes to suppress noise when SNES is off.

## ⚠️ Warning: Position 14 = HWREV0

Position 14 (MCU pin 17 = P1.31) is used by the firmware as **HWREV0** — the least
significant bit of the 8-bit hardware revision ID. It's configured with a pull-up
resistor and read at boot by `get_hwinfo()` in [hwinfo.c](../../../../src/hwinfo.c).

**If you connect anything to this pin**, ensure it's high-impedance during boot,
or the detected hardware revision will change, potentially causing firmware to
misidentify the board model (sd2snes vs FXPAK Pro) or maker.

After boot, the pin is not re-read, so it's safe to drive it for other purposes
during normal operation.

## Verification Notes

- **Pos 7 (square pad)**: Confirmed 3.28V relative to pos 6 (GND) — it's VDD.
  The header has two VDD taps (pos 7 and pos 13) and one GND (pos 6).

- **Pos 5 dual-beep**: Confirmed connecting to MCU pins 14 AND 16. This is expected —
  RESET (pin 14) has a pullup to VDD (pin 16). The low-resistance path through the
  pullup resistor triggers continuity on both.

## Other Unpopulated Headers

The Rev Z board has other unsoldered breakouts besides P401. These may include:
- FPGA debug/configuration (JTAG for the Cyclone IV)
- Additional GPIO breakout
- Test points for analog signals

## Reference
- [MCU Pin Map](mcu-pins.md) — which pins are used vs free
- [LPC1756 Datasheet](https://www.nxp.com/docs/en/data-sheet/LPC1759_58_56_54_52_51.pdf) — Table 5 has LQFP80 pin assignments
