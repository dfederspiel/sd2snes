/*
 * ESP32 Sidecar POC for FXPAK Pro
 *
 * Wiring (P401 header on FXPAK Pro):
 *   ESP32 GPIO4  (RX) <- P401 pos 8  (MCU TXD0 / P0.2)  UART0 data @ 115200
 *   ESP32 GPIO2  (TX) -> P401 pos 1  (MCU RXD0 / P0.3)  UART0 data @ 115200
 *   ESP32 GPIO34 (RX) <- P401 pos 12 (MCU TXD3 / P0.25) debug log @ 921600
 *   ESP32 GND         -- P401 pos 6  (GND)
 *
 * Protocol: ASCII lines in the format $CMD:PAYLOAD\n
 *   MCU sends $PING:N  -> ESP32 responds $PONG:N
 */

#define FXPAK_SERIAL Serial2   /* UART2: bidirectional data link */
#define DEBUG_SERIAL Serial1   /* UART1: read-only MCU debug tap */

#define FXPAK_BAUD   115200
#define FXPAK_RX     4
#define FXPAK_TX     2

#define DEBUG_BAUD   921600
#define DEBUG_RX     34        /* GPIO34 = input-only, perfect for RX */
#define DEBUG_TX     -1        /* not connected (read-only) */

unsigned long lastHB = 0;
unsigned long hbCount = 0;

void setup() {
  Serial.begin(115200);
  /* Pull-up on RX pins so they idle HIGH when SNES is off */
  pinMode(FXPAK_RX, INPUT_PULLUP);
  pinMode(DEBUG_RX, INPUT_PULLUP);
  FXPAK_SERIAL.begin(FXPAK_BAUD, SERIAL_8N1, FXPAK_RX, FXPAK_TX);
  DEBUG_SERIAL.begin(DEBUG_BAUD, SERIAL_8N1, DEBUG_RX, DEBUG_TX);
  Serial.println("ESP32 Sidecar POC ready");
  Serial.println("  UART2: FXPAK data on GPIO4/GPIO2 @ 115200");
  Serial.println("  UART1: MCU debug tap on GPIO34 @ 921600");
}

String rxLine = "";

void loop() {
  /* --- FXPAK data link (UART2 on GPIO4/GPIO2) --- */
  while (FXPAK_SERIAL.available()) {
    char c = FXPAK_SERIAL.read();

    if (c == '\n') {
      if (rxLine.length() > 0) {
        processLine(rxLine);
      }
      rxLine = "";
    } else if (c == '\r') {
      /* skip CR */
    } else if (c >= 0x20 && c < 0x7F && rxLine.length() < 80) {
      rxLine += c;
    }
    /* silently discard non-printable bytes (noise when SNES is off) */
  }

  /* --- MCU debug tap (UART1 on GPIO34, read-only) --- */
  while (DEBUG_SERIAL.available()) {
    char c = DEBUG_SERIAL.read();
    /* Only pass through printable ASCII + newlines (suppress power-off noise) */
    if (c == '\n' || c == '\r' || (c >= 0x20 && c < 0x7F)) {
      Serial.write(c);
    }
  }

  /* Send heartbeat every 3 seconds */
  if (millis() - lastHB >= 3000) {
    lastHB = millis();
    String hb = "$HELLO:" + String(hbCount++);
    FXPAK_SERIAL.println(hb);
    Serial.print("ESP>> ");
    Serial.println(hb);
  }
}

void processLine(String line) {
  Serial.print("MCU>> ");
  Serial.println(line);

  if (line.startsWith("$PING:")) {
    String seq = line.substring(6);
    String response = "$PONG:" + seq;
    FXPAK_SERIAL.println(response);
    Serial.print("ESP<< ");
    Serial.println(response);
  }
  else if (line.startsWith("$HELLO:")) {
    Serial.println("  (MCU says hello!)");
  }
  else if (line == "$INFO?") {
    FXPAK_SERIAL.println("$INFO:ESP32,POC-v0.1");
    Serial.println("ESP<< $INFO:ESP32,POC-v0.1");
  }
  else {
    Serial.print("  (unhandled: ");
    Serial.print(line);
    Serial.println(")");
  }
}
