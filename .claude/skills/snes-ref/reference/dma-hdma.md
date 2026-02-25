# SNES DMA & HDMA Reference

Source: Nintendo SNES Development Manual, Book I — Section 17 (DMA), Tables 2-17-1 and 2-17-2 (B-Bus Address Patterns), Section 17.1.3 (GPDMA Setup), Section 17.3 (HDMA Setup), Chapter 27 (Register Definitions).

## Overview

The SNES has **8 DMA channels** (CH0-CH7) that transfer data between:
- **A-Bus**: CPU address space ($000000-$FFFFFF) — ROM, WRAM, etc.
- **B-Bus**: PPU registers ($2100-$21FF) — VRAM, CGRAM, OAM, etc.

Two DMA types:
- **General Purpose DMA (GPDMA)**: Bulk transfers during Forced Blank or V-Blank. CPU halts until complete.
- **H-Blank DMA (HDMA)**: Per-scanline register writes during active display. Runs automatically every H-Blank.

**Priority**: Channels 0-7 execute in order (CH0 first). HDMA has higher priority than GPDMA — an active HDMA transfer can interrupt a GPDMA transfer mid-stream.

**Speed**: All DMA transfers run at 2.68 MHz regardless of the MEMSEL ($420D) ROM speed setting.

## Channel Registers ($43x0-$43xA)

Each channel x (0-7) has these registers:

| Register | Name | Purpose |
|----------|------|---------|
| $43x0 | DMAPx | Control: direction, addressing mode, transfer mode |
| $43x1 | BBADx | B-Bus address (PPU register, low byte only) |
| $43x2 | A1TxL | A-Bus address low byte |
| $43x3 | A1TxH | A-Bus address high byte |
| $43x4 | A1TxB | A-Bus address bank byte |
| $43x5 | DASxL | Byte count low (GPDMA) / Indirect addr low (HDMA) |
| $43x6 | DASxH | Byte count high (GPDMA) / Indirect addr high (HDMA) |
| $43x7 | DASBx | Indirect HDMA data bank |
| $43x8 | A2AxL | HDMA table current address low (internal) |
| $43x9 | A2AxH | HDMA table current address high (internal) |
| $43xA | NTRLx | HDMA line counter (internal) |

### $43x0 — DMAPx (Control Register)

```
D7     D6      D5   D4    D3     D2   D1   D0
Dir    HDMA    (reserved)  A-adj  Transfer Mode
       Addr
```

**D7 — Direction**:
- 0 = A-Bus → B-Bus (CPU memory → PPU registers) — **most common**
- 1 = B-Bus → A-Bus (PPU registers → CPU memory) — used for VRAM reads

**D6 — HDMA Addressing Mode** (HDMA only, ignored for GPDMA):
- 0 = Absolute addressing (data inline in table)
- 1 = Indirect addressing (table contains pointers to data)

**D4-D3 — A-Bus Address Adjustment** (GPDMA only):
| D4 | D3 | Effect |
|----|-----|--------|
| 0 | 0 | Auto-increment A-bus address after each byte |
| 0 | 1 | Auto-decrement A-bus address after each byte |
| 1 | 0 | Fixed A-bus address (same byte repeated) |
| 1 | 1 | Fixed A-bus address (same byte repeated) |

**D2-D0 — Transfer Mode** (determines B-bus addressing pattern):

| Mode | GPDMA Pattern | HDMA Pattern | Bytes/unit |
|------|---------------|--------------|------------|
| 0 (000) | → B | → B | 1 |
| 1 (001) | → B, → B+1 | → B, → B+1 | 2 |
| 2 (010) | → B, → B | → B, → B | 2 |
| 3 (011) | → B, → B, → B+1, → B+1 | → B, → B, → B+1, → B+1 | 4 |
| 4 (100) | → B, → B+1, → B+2, → B+3 | → B, → B+1, → B+2, → B+3 | 4 |
| 5 (101) | → B, → B+1 (repeat ×2) | → B, → B+1 (repeat ×2) | 4 |

## B-Bus Address Patterns (Detail)

### GPDMA B-Bus Patterns (Table 2-17-1)

For a B-bus base address B, each transfer mode cycles through addresses as successive bytes are transferred:

**Mode 0** — 1 byte, 1 register:
```
Byte:  1st  2nd  3rd  4th  5th  6th  ...
B-Bus:  B    B    B    B    B    B   ...
```
Use: Single-register writes (CGDATA $22, OAMDATA $04)

**Mode 1** — 2 bytes, 2 registers:
```
Byte:  1st  2nd  3rd  4th  5th  6th  ...
B-Bus:  B   B+1   B   B+1   B   B+1 ...
```
Use: VRAM writes via VMDATAL/H ($18/$19)

**Mode 2** — 2 bytes, 1 register (write-twice):
```
Byte:  1st  2nd  3rd  4th  5th  6th  ...
B-Bus:  B    B    B    B    B    B   ...
```
Use: Write-twice registers like scroll ($210D — write low then high)

**Mode 3** — 4 bytes, 2 registers (write-twice each):
```
Byte:  1st  2nd  3rd  4th  5th  6th  7th  8th  ...
B-Bus:  B    B   B+1  B+1   B    B   B+1  B+1  ...
```
Use: Two write-twice registers in sequence (e.g., BG1HOFS + BG1VOFS)

**Mode 4** — 4 bytes, 4 registers:
```
Byte:  1st  2nd  3rd  4th  5th  6th  7th  8th  ...
B-Bus:  B   B+1  B+2  B+3   B   B+1  B+2  B+3  ...
```
Use: Four consecutive registers

**Mode 5** — 4 bytes, 2 registers (alternating, repeated):
```
Byte:  1st  2nd  3rd  4th  5th  6th  7th  8th  ...
B-Bus:  B   B+1   B   B+1   B   B+1   B   B+1  ...
```
Use: Like mode 1 but 4 bytes per unit (two writes to each register pair)

### HDMA B-Bus Patterns (Table 2-17-2)

HDMA transfers a fixed number of bytes **per scanline**. The B-bus pattern per line:

**Mode 0** — 1 byte/line:
```
Per line: → B
Data table: 1 byte per line
```

**Mode 1** — 2 bytes/line:
```
Per line: → B, → B+1
Data table: 2 bytes per line
```

**Mode 2** — 2 bytes/line (same register):
```
Per line: → B, → B
Data table: 2 bytes per line (low, high for write-twice registers)
```

**Mode 3** — 4 bytes/line:
```
Per line: → B, → B, → B+1, → B+1
Data table: 4 bytes per line
```

**Mode 4** — 4 bytes/line:
```
Per line: → B, → B+1, → B+2, → B+3
Data table: 4 bytes per line
```

## Trigger Registers

### $420B — MDMAEN (General Purpose DMA Enable)

```
D7   D6   D5   D4   D3   D2   D1   D0
CH7  CH6  CH5  CH4  CH3  CH2  CH1  CH0
```

- Writing 1 to a bit **immediately triggers** that channel's DMA transfer
- CPU halts during transfer
- Bit **auto-clears** when transfer completes
- Multiple bits can be set simultaneously — channels execute sequentially (CH0 first)
- **Only write during V-Blank or Forced Blank** for VRAM/CGRAM/OAM transfers

### $420C — HDMAEN (H-Blank DMA Enable)

```
D7   D6   D5   D4   D3   D2   D1   D0
CH7  CH6  CH5  CH4  CH3  CH2  CH1  CH0
```

- Writing 1 to a bit **enables** that channel for HDMA
- Channel is **auto-initialized** at the start of each frame (V-Blank)
- Transfers execute **every H-Blank** (once per scanline) during active display
- Bit **persists** until cleared by software (unlike GPDMA)
- Write during V-Blank for proper initialization

## General Purpose DMA (GPDMA)

### How It Works

1. Set up channel registers ($43x0-$43x6)
2. Write channel enable bit to $420B
3. CPU immediately halts
4. DMA hardware transfers bytes: A-bus ↔ B-bus
5. A-bus address increments/decrements/stays fixed per D4-D3
6. B-bus address cycles per transfer mode
7. Byte count decrements; transfer stops at 0
8. Channel bit in $420B auto-clears
9. CPU resumes

### Byte Count Special Case

When $43x5/$43x6 = $0000, the DMA transfers **65,536 bytes** ($10000), not zero. This is the maximum single-channel transfer.

### GPDMA Setup Sequence (from Manual Section 17.1.3)

The manual shows two examples:

**Example 1: Forced Blank transfer (CH4)**
```
Phase: Forced Blank ($2100 bit 7 = 1)

1. Set $4340 = transfer mode + direction
   - D7=0 (A→B), D3-D4=00 (increment), D2-D0=mode
2. Set $4341 = B-bus destination register
3. Set $4342/$4343/$4344 = 24-bit A-bus source address
4. Set $4345/$4346 = byte count
5. Write $420B = $10 (enable CH4, bit 4)
   → Transfer executes immediately
```

**Example 2: V-Blank transfer (CH3)**
```
Phase: During V-Blank (NMI handler)

1. Set $4330 = transfer mode + direction
2. Set $4331 = B-bus destination
3. Set $4332/$4333/$4334 = A-bus source
4. Set $4335/$4336 = byte count
5. Write $420B = $08 (enable CH3, bit 3)
   → Transfer executes immediately within V-Blank
```

### DMA7 Macro (sd2snes codebase)

The `dma.i65` macro uses channel 7 for all GPDMA transfers:

```asm
; snescom syntax:
DMA7(#$01, #$0800, #^tile_data, #!tile_data, #$18)
;     mode  length   bank         addr          B-reg

; Expands to:
  php
  sep #$20 : .as
  rep #$10 : .xl
  lda #$01          ; mode: 2 bytes → $18/$19 (VMDATAL/H)
  sta $4370         ; CH7 control
  ldx #!tile_data   ; A-bus address (16-bit)
  lda #^tile_data   ; A-bus bank
  stx $4372
  sta $4374
  ldx #$0800        ; byte count
  stx $4375
  lda #$18          ; B-bus = VMDATAL
  sta $4371
  lda #$80          ; enable CH7
  sta $420B         ; TRIGGER
  plp
```

**Key points**:
- Always uses CH7 (bit 7 = $80 in $420B)
- `php`/`plp` preserves processor state (critical for caller safety)
- Mode $01 is the most common — writes to VMDATAL ($18) and VMDATAH ($19) alternately

### Common GPDMA Transfer Modes

| Mode | B-reg | Purpose | Example |
|------|-------|---------|---------|
| $00 | $04 | OAM data (1 byte/write) | `DMA7(#$00, #$220, ...)` |
| $00 | $22 | CGRAM palette (1 byte/write) | `DMA7(#$00, #$200, ...)` |
| $01 | $18 | VRAM data (2 bytes: low+high) | `DMA7(#$01, #$2000, ...)` |
| $02 | $10 | BG2VOFS write-twice | scroll DMA |
| $08 | $04 | OAM fill from fixed addr | `DMA7(#$08, #$220, ...)` |

Mode $08 = fixed A-bus address ($08 = D3=1, D2-D0=000). Reads the same byte repeatedly — useful for filling OAM/VRAM with a single value (e.g., clearing to zero).

## H-Blank DMA (HDMA)

### How It Works

HDMA writes PPU register values **every scanline** during active display. This enables per-scanline effects: gradients, wavy scrolls, window shape changes, mode switches.

1. Set up channel registers ($43x0-$43x4, optionally $43x7)
2. Write enable bits to $420C during V-Blank
3. At V-Blank start: HDMA auto-initializes (loads table pointer into internal registers)
4. Each H-Blank during active display:
   - Read entry from HDMA table
   - Write data bytes to B-bus register(s)
   - Decrement line counter
   - When counter reaches 0, advance to next table entry
5. Table terminated by $00 entry
6. Repeats from start next frame (auto-reinitializes)

### HDMA Table Format

#### Absolute Addressing (D6=0 in $43x0)

```
Table in ROM/WRAM (pointed to by $43x2-$43x4):

  [count_byte] [data_byte_1] [data_byte_2] ...
  [count_byte] [data_byte_1] [data_byte_2] ...
  ...
  [$00]         ; terminator
```

**count_byte** format:
```
D7     D6-D0
C-flag Line count (1-127)
```

- **C=0 (bit 7 clear)**: **Repeat mode** — same data for all `count` scanlines
- **C=1 (bit 7 set)**: **Continuous mode** — new data bytes for each of the `count & $7F` scanlines

Number of data bytes per entry = determined by transfer mode:
- Mode 0: 1 byte
- Mode 1: 2 bytes
- Mode 2: 2 bytes
- Mode 3: 4 bytes
- Mode 4: 4 bytes

**Repeat mode example** (mode 0, 1 byte):
```
  .byt 10, $0F    ; 10 scanlines, all write $0F to B-bus register
  .byt  5, $08    ;  5 scanlines, all write $08
  .byt $00        ; end
```

**Continuous mode example** (mode 0, 1 byte):
```
  .byt $83        ; C=1, 3 scanlines with NEW data each line
  .byt $1F        ;   line 1: write $1F
  .byt $10        ;   line 2: write $10
  .byt $08        ;   line 3: write $08
  .byt $00        ; end
```

#### Indirect Addressing (D6=1 in $43x0)

Instead of inline data, the table contains **pointers** to data:

```
Table (pointed to by $43x2-$43x4):

  [count_byte] [data_addr_low] [data_addr_high]
  [count_byte] [data_addr_low] [data_addr_high]
  ...
  [$00]         ; terminator

Data bank: set in $43x7 (DASBx)
```

The HDMA hardware reads `data_addr` from the table, then fetches actual data from `{$43x7}:{data_addr}`. This allows:
- Multiple table entries to point to the same data (save ROM space)
- Dynamic data changes (point to WRAM, modify data each frame)

### HDMA Setup Sequence (from Manual Section 17.3)

**Example 1: Indirect addressing (CH0)**
```
1. Set $4300 = mode + direction + D6=1 (indirect)
   - D6=1 for indirect addressing
   - D2-D0 = transfer mode
2. Set $4301 = B-bus register
3. Set $4302/$4303/$4304 = 24-bit table address
4. Set $4307 = data bank (for indirect pointers)
5. Write $420C |= $01 (enable CH0) during V-Blank
```

**Example 2: Absolute addressing (CH1)**
```
1. Set $4310 = mode + direction + D6=0 (absolute)
2. Set $4311 = B-bus register
3. Set $4312/$4313/$4314 = 24-bit table address
4. Write $420C |= $02 (enable CH1) during V-Blank
```

**Important**: Set up all HDMA channels before enabling them. Write $420C once with all channel bits, not incrementally.

## sd2snes Menu HDMA Configuration

The menu uses 6 HDMA channels configured in `setup_hdma` (`dma.a65`):

### Channel 0 — BG2 Vertical Scroll ($2110)
```asm
  lda #$02            ; mode 2: write-twice, 1 register
  sta $4300
  lda #$10            ; B-bus = $2110 (BG2VOFS)
  sta $4301
  ; A-bus → hdma_bg2scroll table
```
Mode 2 writes low then high byte to the same register (BG2VOFS is write-twice).

### Channel 1 — CGRAM Address ($2121)
```asm
  lda #$00            ; mode 0: 1 byte, 1 register
  sta $4310
  lda #$21            ; B-bus = $2121 (CGADD)
  sta $4311
  ; A-bus → hdma_cg_addr table (always writes $00)
```
Resets CGRAM address to 0 every scanline group so channel 2 always writes color 0.

### Channel 2 — CGRAM Data ($2122)
```asm
  lda #$02            ; mode 2: 2 bytes, write-twice register
  sta $4320
  lda #$22            ; B-bus = $2122 (CGDATA)
  sta $4321
  ; A-bus → hdma_pal table (BGR555 gradient colors)
```
Writes 2-byte BGR555 color to CGDATA each scanline group. Combined with channel 1, this creates the background gradient.

### Channel 3 — BG Mode Switch ($2105)
```asm
  lda #$00            ; mode 0: 1 byte, 1 register
  sta $4330
  lda #$05            ; B-bus = $2105 (BGMODE)
  sta $4331
  ; A-bus → hdma_mode table
```
Switches BG mode between regions (Mode 3 for logo area, Mode 5 for text area).

### Channel 4 — BG1 Horizontal Scroll ($210D)
```asm
  lda #$03            ; mode 3: 4 bytes, 2 write-twice registers
  sta $4340
  lda #$0d            ; B-bus = $210D (BG1HOFS), also $210E (BG1VOFS)
  sta $4341
  ; A-bus → hdma_bg1scroll table (4 bytes: H-low, H-high, V-low, V-high)
```
Mode 3 writes to $210D twice (BG1HOFS low/high) then $210E twice (BG1VOFS low/high).

### Channel 5 — Color Math ($2131 + $2132)
```asm
  lda #$01            ; mode 1: 2 bytes, 2 registers
  sta $4350
  lda #$31            ; B-bus = $2131 (CGADSUB), then $2132 (COLDATA)
  sta $4351
  ; A-bus → hdma_math table (2 bytes: math_mode, coldata)
```
Mode 1 writes to CGADSUB ($2131) and COLDATA ($2132) per scanline group. This controls the selection bar's color math effect.

### Enable All Channels
```asm
  lda #$3f            ; bits 0-5 = channels 0-5
  sta $420c           ; enable HDMA
  lda #$81            ; NMI + auto joypad
  sta $4200           ; enable NMI
```

## Channel Allocation Best Practices

### Don't Mix GPDMA and HDMA on Same Channel

A channel is either GPDMA or HDMA, not both simultaneously. The sd2snes menu uses:
- **CH0-CH5**: HDMA (setup_hdma)
- **CH7**: GPDMA (DMA7 macro)
- **CH6**: Available

### HDMA Priority

If HDMA and GPDMA channels are both active, HDMA takes priority. An HDMA transfer at H-Blank will **pause** a running GPDMA transfer, complete the HDMA bytes, then resume GPDMA. This means:

- Large GPDMA transfers during active display will be interrupted every scanline
- Best practice: do GPDMA only during V-Blank or Forced Blank

### Channel Priority

When multiple GPDMA channels are triggered simultaneously ($420B with multiple bits), they execute in order: CH0 first, CH7 last.

## Common DMA Recipes

### Clear VRAM (fill with zeros)
```asm
; Set VRAM address to 0
  ldx #$0000
  stx $2116
  lda #$80            ; increment on high byte write
  sta $2115
; DMA mode $09 = A→B, fixed addr, mode 1 (2-reg)
  DMA7(#$09, #$0000, #^zero, #!zero, #$18)
; $0000 byte count = 65536 bytes = fill all 32K words
```

### Load Palette to CGRAM
```asm
  lda #$00
  sta $2121           ; CGRAM address 0
  DMA7(#$00, #$0200, #^palette, #!palette, #$22)
; Mode $00 = 1 byte/write to CGDATA ($22)
; $0200 = 512 bytes = 256 colors
```

### Load Tiles to VRAM
```asm
  ldx #$6000          ; VRAM destination word address
  stx $2116
  lda #$80
  sta $2115           ; increment after high byte
  DMA7(#$01, #$1000, #^tiles, #!tiles, #$18)
; Mode $01 = 2 bytes/write to VMDATAL/H ($18/$19)
; $1000 = 4096 bytes of tile data
```

### Load OAM
```asm
; Set OAM address
  ldx #$0000
  stx $2102
; DMA full OAM (544 bytes)
  DMA7(#$00, #$0220, #^oam_buf, #!oam_buf, #$04)
; Mode $00 = 1 byte/write to OAMDATA ($04)
```

### Simple HDMA Gradient (1 channel, absolute)
```asm
; Channel 2: write BGR555 color to CGRAM address 0 per scanline group
; Requires channel 1 to reset CGADD to 0 each time

; Channel 2 setup:
  lda #$02            ; mode 2: write-twice (2 bytes → same register)
  sta $4320
  lda #$22            ; B-bus = CGDATA ($2122)
  sta $4321
  lda #^gradient_table
  ldy #!gradient_table
  sty $4322
  sta $4324

gradient_table
  .byt 32             ; 32 lines, same color (repeat mode)
  .byt $00, $00       ; black
  .byt 32
  .byt $00, $40       ; dark blue
  .byt 32
  .byt $00, $7c       ; bright blue
  .byt $00            ; end
```

## Timing Constraints

### V-Blank Window

Source: Manual Chapter 17 (DMA budget), Chapter 21 (timing), Chapter 23 (System Flowchart NCL PG 40-42).

NTSC frame: 262 total scanlines, 224 display lines = **38 V-Blank lines**.
Each scanline = 63.5 us (H counter runs 0-339, each step = 0.186 us).

**V-Blank duration**: 38 lines x 63.5 us = ~2,413 us.

**DMA budget**: The manual states that for 224-line mode, general-purpose DMA can transfer a maximum of **6K bytes (6,144 bytes)** during V-Blank. At the DMA clock of 2.68 MHz, this works out to ~1 byte per machine cycle.

**Auto-joypad overhead**: When enabled ($4200 bit 0 = 1), the hardware reads joypads starting 18 us (48 machine cycles) after V-Blank begins. The read takes **215 us** (~580 machine cycles / ~580 bytes of DMA time). The manual recommends starting DMA immediately at V-Blank — the DMA byte count itself serves as a timer for when joypad data is ready.

**Practical budget**: ~6,144 bytes minus HDMA init overhead (each active HDMA channel re-reads its table pointer at V-Blank start). With 6 HDMA channels active, budget approximately **5,500-6,000 bytes** for GPDMA.

### System Flowchart (Chapter 23)

The Nintendo-recommended main loop structure (from NCL PG 40-42):

```
[INIT — during Forced Blank]
  1. Write $8F to $2100 (forced blank on)
  2. Clear all registers (Chapter 26)
  3. Set PPU registers: BGMODE, base addresses, OBJ settings
  4. Set main screen register $212C
  5. OAM/CGRAM data settings (set OAM addr $2102=$00, CG addr $2121=$00)
  6. DMA OAM + CGRAM data (2 channels of GPDMA)
  7. Set VRAM address mode ($2115), VRAM address ($2116/$2117)
  8. DMA VRAM data (OBJ/BG character data, BG tilemap data) — loop until done
  9. Set registers for initial screen display
  10. Write $0F to $2100 (release forced blank, full brightness)

[MAIN LOOP — display period]
  11. Generate/update data in WRAM for next frame's BG/OBJ changes
  12. Write $81 to $4200 (enable NMI + auto joypad)
  13. Wait for NMI...

[NMI HANDLER — V-Blank period]
  14. DMA renewed OAM data
  15. Update BG/OBJ register settings for this frame
  (Auto-joypad completes ~215 us after V-Blank start)

[RETURN TO MAIN LOOP — display period]
  16. Read joypad data from $4218-$421F
  17. Process input, update game state
  18. Loop to step 11
```

**Key insight from the flowchart**: OAM and CGRAM are DMA'd first during init (step 6), VRAM second (step 8). During the main loop, the NMI handler owns all PPU writes — the main thread only writes to WRAM buffers.

### PPU Memory Access Windows

Source: Manual Chapter 24, Caution #2.

| Target | Forced Blank | V-Blank | H-Blank | Active Display |
|--------|:------------:|:-------:|:-------:|:--------------:|
| VRAM ($2118/$2119) | OK | OK | **NO** | **NO** |
| OAM ($2104) | OK | OK | **NO** | **NO** |
| CGRAM ($2122) | OK | OK | **OK** | **NO** |
| Other PPU regs (write) | OK | OK | OK | OK (may glitch) |
| Other PPU regs (read) | OK | OK | OK | OK (may be stale) |

**CGRAM is unique**: It can be written during H-Blank, which is why HDMA-driven gradients work — HDMA channels 1+2 in the sd2snes menu write CGADD/CGDATA every H-Blank to change background color 0 per scanline group.

**VRAM and OAM are stricter**: Only V-Blank or Forced Blank. Writing during active display produces garbage. This is why the NMI handler DMAs tile buffers and OAM — it runs at the start of V-Blank.

**Write-twice latch reset** (Chapter 24, Caution #1): CGDATA ($2122) uses a low/high byte latch. If you're unsure whether the latch is in the low or high state, write the CGRAM address again via $2121 to reset it. This reinitializes the two-write sequence.

### H-Blank Window

HDMA transfers happen during each H-Blank (~16-40 CPU cycles depending on rendering). Each HDMA channel transfers its data bytes (1-4 per channel per line). With 6 active channels like the sd2snes menu, that's up to 16 bytes per H-Blank — well within limits.

### Forced Blank

During Forced Blank ($2100 bit 7 = 1), there are no timing constraints. DMA can transfer unlimited data to VRAM/CGRAM/OAM. The screen shows no picture.

Best practice: Do all initial data loading during Forced Blank at boot, then use V-Blank DMA for incremental updates.
