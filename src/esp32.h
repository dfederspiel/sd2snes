/*

   esp32.h: ESP32 sidecar communication via UART0

*/

#ifndef ESP32_H
#define ESP32_H

void esp32_init(void);        /* call after PLL connected */
void esp32_poll(void);
void esp32_send(const char *cmd, const char *payload);

#endif
