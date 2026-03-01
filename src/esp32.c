/*

   esp32.c: ESP32 sidecar communication via UART0

   UART0 driver (separate from the macro-based UART3 debug driver)
   with a simple ASCII line protocol for ESP32 commands.

   Wiring (P401 header):
     pos 8 (P0.2/TXD0) -> ESP32 GPIO4 (RX)
     pos 1 (P0.3/RXD0) <- ESP32 GPIO2 (TX)
     pos 6 (GND)        -- ESP32 GND

*/

#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include "bits.h"
#include "config.h"
#include "esp32.h"

/* UART0 register access */
#define ESP_UART LPC_UART0

/* RX line buffer (80 bytes max per line) */
#define ESP_RXBUF_SIZE 80
static char esp_rxbuf[ESP_RXBUF_SIZE];
static volatile uint8_t esp_rxpos;
static volatile uint8_t esp_line_ready;

/* Ping state */
static uint32_t esp_ping_seq;
static uint32_t esp_poll_count;
#define ESP_PING_INTERVAL 100  /* ~2 seconds at 20ms poll rate */

/* ---- UART0 ISR (RX only) ---- */

void UART0_IRQHandler(void) {
  int iir = ESP_UART->IIR;
  if (!(iir & 1)) {
    switch (iir & 14) {
    case 2: /* THR empty - we don't use interrupt-driven TX */
      BITBAND(ESP_UART->IER, 1) = 0;
      break;

    case 4:  /* RDA - data received */
    case 12: /* CTI - character timeout */
      while (BITBAND(ESP_UART->LSR, 0)) {
        char c = ESP_UART->RBR;
        if (c == '\n') {
          if (!esp_line_ready && esp_rxpos < ESP_RXBUF_SIZE) {
            esp_rxbuf[esp_rxpos] = '\0';
            esp_line_ready = 1;
          }
        } else if (c != '\r' && !esp_line_ready) {
          if (esp_rxpos < ESP_RXBUF_SIZE - 1) {
            esp_rxbuf[esp_rxpos++] = c;
          }
        }
      }
      break;

    case 6: /* RX line status error */
      (void)ESP_UART->LSR;
      break;

    default:
      break;
    }
  }
}

/* ---- TX functions (polling, simple) ---- */

static void esp_putc(char c) {
  while (!(ESP_UART->LSR & (1 << 5))) ; /* wait for THR empty */
  ESP_UART->THR = (unsigned char)c;
}

void esp32_send(const char *cmd, const char *payload) {
  esp_putc('$');
  while (*cmd) esp_putc(*cmd++);
  if (payload && *payload) {
    esp_putc(':');
    while (*payload) esp_putc(*payload++);
  }
  esp_putc('\r');
  esp_putc('\n');
}

/* ---- RX line handler ---- */

static void esp32_handle_line(void) {
  char *line = (char *)esp_rxbuf;

  if (line[0] != '$') {
    printf("[ESP32] raw: %s\n", line);
    return;
  }

  line++; /* skip $ */

  /* Find colon separator */
  char *colon = strchr(line, ':');
  char *payload = "";
  if (colon) {
    *colon = '\0';
    payload = colon + 1;
  }

  if (strcmp(line, "PONG") == 0) {
    printf("[ESP32] PONG seq=%s\n", payload);
  } else if (strcmp(line, "HELLO") == 0) {
    printf("[ESP32] Hello from ESP32: %s\n", payload);
  } else if (strcmp(line, "WIFI") == 0) {
    printf("[ESP32] WiFi: %s\n", payload);
  } else if (strcmp(line, "INFO") == 0) {
    printf("[ESP32] Info: %s\n", payload);
  } else {
    printf("[ESP32] unknown: %s\n", line);
  }
}

/* ---- Public API ---- */

void esp32_poll(void) {
  if (esp_line_ready) {
    esp32_handle_line();
    esp_rxpos = 0;
    esp_line_ready = 0;
  }

  esp_poll_count++;
  if (esp_poll_count >= ESP_PING_INTERVAL) {
    esp_poll_count = 0;
    char seq[12];
    snprintf(seq, sizeof(seq), "%lu", (unsigned long)esp_ping_seq++);
    esp32_send("PING", seq);
  }
}

/* ---- UART0 init ---- */

void esp32_init(void) {
  /* 1. Power on UART0 */
  BITBAND(LPC_SC->PCONP, 3) = 1;

  /* 2. Configure 115200 8N1.  PCLK = CCLK/4 = 24MHz, DLL = 13 */
  ESP_UART->LCR = BV(7) | 3;   /* DLAB=1, 8N1 */
  ESP_UART->DLL = 13;
  ESP_UART->DLM = 0;
  ESP_UART->FDR = 0x10;         /* MULVAL=1, DIVADDVAL=0 */
  BITBAND(ESP_UART->LCR, 7) = 0; /* DLAB=0 */
  ESP_UART->FCR = BV(0) | BV(1) | BV(2); /* enable + reset FIFOs */

  /* 3. Connect pins (UART0 configured, TXD0 idles high) */
  GPIO_MODE_AF(LPC_GPIO0, 2, 1); /* P0.2 = TXD0 */
  GPIO_MODE_AF(LPC_GPIO0, 3, 1); /* P0.3 = RXD0 */

  /* 4. Enable RX interrupt */
  ESP_UART->IER = BV(0);
  NVIC_EnableIRQ(UART0_IRQn);

  /* 5. Init state */
  esp_rxpos = 0;
  esp_line_ready = 0;
  esp_ping_seq = 0;
  esp_poll_count = 0;

  printf("[ESP32] UART0 ready (115200 8N1, DLL=13)\n");
  esp32_send("HELLO", "fxpak");
}
