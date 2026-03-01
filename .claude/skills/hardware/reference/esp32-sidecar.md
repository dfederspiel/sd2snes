# ESP32 Sidecar — FXPAK Pro UART0 Communication

## Status: PROVEN WORKING (2026-03-01)

Bidirectional MCU↔ESP32 serial communication over UART0 via the P401 header.
Foundation for WiFi file downloads, NTP clock sync, and remote management.

## Wiring (4 wires, no MCU soldering)

```
P401 pos 8 (MCU P0.2/TXD0) ──→ ESP32 GPIO4 (RX2)     Data link
P401 pos 1 (MCU P0.3/RXD0) ←── ESP32 GPIO2 (TX2)     Data link
P401 pos 12 (MCU P0.25/TXD3) ─→ ESP32 GPIO34 (RX1)   Debug tap (read-only)
P401 pos 6 (GND)             ─── ESP32 GND
ESP32 powered via its own USB cable
```

### ESP32 Pin Warning

ESP32-WROOM-32 DevKit V1 boards label GPIO1/GPIO3 as "TXD0/RXD0" on the silk screen.
These are the **USB serial pins** (Serial/UART0) — connecting to them does NOT work for
Serial2 communication. You must use the actual GPIO number pins matching the
`Serial2.begin()` call. GPIO4 and GPIO2 are on the right side of the board, labeled
as digital pin numbers, not as "TX/RX".

**This was the #1 time sink during development** — multiple sessions of debugging garbled
data before discovering the wires were on the wrong pins entirely.

## Protocol

ASCII line protocol for debuggability:
```
$CMD:PAYLOAD\r\n
```

Current commands:
| Direction | Command | Purpose |
|-----------|---------|---------|
| MCU→ESP32 | `$PING:N` | Heartbeat (every ~2 seconds) |
| ESP32→MCU | `$PONG:N` | Heartbeat response |
| MCU→ESP32 | `$HELLO:fxpak` | Sent once at init |
| ESP32→MCU | `$HELLO:N` | ESP32 heartbeat (every 3 seconds) |

Lines not starting with `$` are logged as raw debug text.

## MCU Side — UART0 Driver (`src/esp32.c`)

### UART0 Configuration
- **Baud**: 115200 8N1
- **PCLK**: CCLK/4 = 24 MHz (PCLKSEL0 bits[7:6] = 0, the LPC1756 default)
- **DLL**: 13 (24000000 / 16 / 13 = 115384 baud, 0.16% error)
- **DLM**: 0
- **FDR**: 0x10 (MULVAL=1, DIVADDVAL=0, no fractional divider)
- **Interrupt**: RX only (IER bit 0). TX uses polling.

### Init Ordering (Critical)

```c
// 1. Power on UART0 — MUST be first
BITBAND(LPC_SC->PCONP, 3) = 1;

// 2. Configure baud rate and FIFO WHILE pins are still GPIO
ESP_UART->LCR = BV(7) | 3;     // DLAB=1, 8N1
ESP_UART->DLL = 13;
ESP_UART->DLM = 0;
ESP_UART->FDR = 0x10;
BITBAND(ESP_UART->LCR, 7) = 0; // DLAB=0
ESP_UART->FCR = BV(0) | BV(1) | BV(2); // enable + reset FIFOs

// 3. THEN connect pins — TXD0 idles HIGH because UART is already configured
GPIO_MODE_AF(LPC_GPIO0, 2, 1); // P0.2 = TXD0
GPIO_MODE_AF(LPC_GPIO0, 3, 1); // P0.3 = RXD0
```

**Why this order matters**: If you connect the pin mux BEFORE powering on and configuring
UART0, the TXD0 output is undefined (LOW). The ESP32 sees a break condition or garbage
framing. The result is all-zero bytes or garbled data on every transmission.

### power_init() Kills UART0

`src/lpc175x/power.c` does a full word write to PCONP that does NOT include bit 3 (UART0).
After `power_init()`, UART0 is powered off. `esp32_init()` must explicitly set bit 3.
Confirmed: PCONP goes from `0xa2a18240` (no UART0) to `0xa2a18248` (UART0 enabled).

### PCLK Discovery

PCLKSEL0 bits[7:6] control the UART0 PCLK divider:
| Bits | Divider | PCLK (at 96 MHz CCLK) | DLL for 115200 |
|------|---------|------------------------|-----------------|
| 00 | CCLK/4 | 24 MHz | **13** |
| 01 | CCLK/1 | 96 MHz | 52 |
| 10 | CCLK/2 | 48 MHz | 26 |
| 11 | CCLK/8 | 12 MHz | 7 |

The default is 00 (CCLK/4). The firmware's `clock_init()` does NOT modify PCLKSEL0 for
UART0, so the default persists. We confirmed bits[7:6]=0 via printf.

**Brute-force method** (used to discover): Try each DLL for 3 seconds, send a test message.
The ESP32 shows which one decodes. DLL=13 was confirmed as the correct value.

### ISR Pattern

`UART0_IRQHandler` handles RX only (IER bit 0). Accumulates characters into `esp_rxbuf[]`
until `\n`, then sets `esp_line_ready = 1`. Main loop calls `esp32_poll()` which checks
the flag, processes the line, and resets the buffer.

TX uses simple polling via `esp_putc()` — waits for THR empty (LSR bit 5), writes byte.
This is adequate for low-frequency command messages.

### Integration Points

```c
// main.c — after clock_init() (PLL connected, PCLK stable)
esp32_init();

// main.c game loop + snes.c menu loop — called every ~20ms
esp32_poll();
```

`esp32_poll()` also sends `$PING:N` every 100 calls (~2 seconds at 20ms poll rate).

## ESP32 Side — Arduino Sketch (`esp32_sidecar/esp32_sidecar.ino`)

Three UART channels:
| UART | Object | Pins | Baud | Purpose |
|------|--------|------|------|---------|
| UART0 | `Serial` | USB | 115200 | Debug monitor (PC terminal) |
| UART2 | `Serial2` (FXPAK_SERIAL) | GPIO4 RX, GPIO2 TX | 115200 | MCU data link |
| UART1 | `Serial1` (DEBUG_SERIAL) | GPIO34 RX, none TX | 921600 | MCU debug tap (read-only) |

### Noise Suppression

When SNES is powered off, RX pins float and produce garbage bytes.
- `INPUT_PULLUP` on GPIO4 and GPIO34 keeps lines idle HIGH
- Non-printable bytes (outside 0x20-0x7E range, excluding \r\n) are silently discarded
- FXPAK data link limits lines to 80 chars

## Firmware Deployment

### Build
```bash
wsl -e bash -c "cd /mnt/c/Users/david/code/sd2snes/src && make CONFIG=config-mk3 VERSION=1.11.1-esp32"
```

### Critical: Version String Must Differ from Stock

The bootloader (`src/bootldr/iap.c`) computes CRC32 of `CONFIG_VERSION` and compares it
to the CRC32 stored in the already-flashed firmware. **If they match, the update is silently
skipped.** Stock firmware uses version `1.11.1`, so building without `VERSION=` produces an
identical CRC and the bootloader ignores the file.

**Always pass a unique VERSION** (e.g., `VERSION=1.11.1-esp32`).

Header format: `[4B "SNS3"][4B version_crc32][4B size][4B data_crc32][4B crcc][236B 0xFF]`

### Deploy to SD Card
```
cp src/obj-mk3/firmware.im3 F:/sd2snes/firmware.im3
```
Power cycle. Bootloader flashes on next boot (LED activity visible).

### Verify
Look for `sd2snes Mk.III +ESP32` in the UART3 debug output (or ESP32 debug tap).

## Debugging Checklist

If communication doesn't work:

1. **Check ESP32 pin connections** — Are you connected to GPIO4/GPIO2 (the actual pin numbers),
   not the USB serial pins (GPIO1/GPIO3 labeled TXD0/RXD0)?

2. **Check firmware is actually flashed** — Look for your custom version string in boot log.
   If you see the stock version, the bootloader skipped your update (version CRC match).

3. **Check init ordering** — PCONP bit 3 must be set BEFORE GPIO_MODE_AF for P0.2/P0.3.

4. **Check PCLK and DLL** — Printf PCLKSEL0 to UART3. Bits[7:6] determine the DLL value.
   If someone modifies clock_init() to change PCLKSEL0, the DLL must be recalculated.

5. **Check for noise** — If SNES is off, RX pins float. Pull-ups + byte filtering required.

6. **Loopback test** — On ESP32, connect GPIO4 to GPIO2 (UART2 TX↔RX). The sketch's
   HELLO heartbeats should echo back as received lines. This proves the ESP32 UART2 works
   independently of the MCU.

## Future Directions

- WiFi file downloads (ESP32 downloads ROM → sends to MCU → writes to SD card)
- NTP clock sync (ESP32 gets time → sends to MCU → sets RTC)
- Remote management (ESP32 serves web UI → sends commands to MCU)
- Higher baud rate (921600 or higher — UART0 supports up to 6 Mbaud with fractional divider)
- Interrupt-driven TX with ring buffer (for higher throughput)
