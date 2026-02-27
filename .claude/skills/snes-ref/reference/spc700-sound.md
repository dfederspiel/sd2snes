# SPC700 Sound System Reference

Reference for the SNES APU (Audio Processing Unit) covering the SPC700 CPU,
DSP registers, BRR sample format, I/O port communication, and the IPL boot
protocol. Validated against SNES Development Manual Book I Section 3 and
Appendices C/D, cross-referenced with the sd2snes menu ROM codebase
(`spc700.a65`, `spcplay.a65`).

---

## Architecture Overview

The SNES sound system is a self-contained module with its own CPU, DSP, and RAM:

- **SPC700 CPU**: 8-bit processor, 2.048 MHz (base clock from ~24.576 MHz ÷ 12)
- **DSP**: 8 voices of 4-bit ADPCM (BRR), hardware ADSR/GAIN envelopes,
  pitch modulation, noise generator, echo with 8-tap FIR filter
- **RAM**: 64KB (512Kbit), shared between CPU and DSP (time-division)
- **D/A Converter**: 16-bit stereo output, 32kHz sample rate

Communication with the SNES main CPU occurs exclusively through 4 bidirectional
I/O ports ($2140-$2143 on SNES side, $F4-$F7 on SPC700 side).

---

## SPC700 Memory Map

| Range | Description |
|---|---|
| $0000-$00EF | Page 0 — RAM (direct page addressing) |
| $00F0-$00FF | Peripheral Function Registers |
| $0100-$01FF | Page 1 — RAM (stack area; SP is 8-bit, always page 1) |
| $0200-$FFBF | RAM — general use, sample data, echo buffer |
| $FFC0-$FFFF | IPL ROM — 64-byte boot loader (can be switched out via $F1 bit 7) |

Total: 64KB address space. All RAM is on the sound module PCB.

### Peripheral Function Registers ($F0-$FF)

| Address | Name | R/W | Reset | Description |
|---|---|---|---|---|
| $F0 | TEST | W | — | Test register (do not use) |
| $F1 | CONTROL | W | --00-000 | Port clear, timer enable, IPL ROM enable |
| $F2 | DSPADDR | R/W | indet. | DSP register address |
| $F3 | DSPDATA | R/W | indet. | DSP register data |
| $F4 | PORT0 | R/W | $00 | I/O Port 0 (R=from SNES, W=to SNES) |
| $F5 | PORT1 | R/W | $00 | I/O Port 1 |
| $F6 | PORT2 | R/W | $00 | I/O Port 2 |
| $F7 | PORT3 | R/W | $00 | I/O Port 3 |
| $F8-$F9 | — | — | — | Unused |
| $FA | TIMER0 | W | indet. | Timer 0 divisor (8kHz base) |
| $FB | TIMER1 | W | indet. | Timer 1 divisor (8kHz base) |
| $FC | TIMER2 | W | indet. | Timer 2 divisor (64kHz base) |
| $FD | COUNTER0 | R | indet. | Timer 0 counter (4-bit, clears on read) |
| $FE | COUNTER1 | R | indet. | Timer 1 counter |
| $FF | COUNTER2 | R | indet. | Timer 2 counter |

### CONTROL register ($F1) bits

| Bit | Function |
|---|---|
| 7 | IPL ROM enable (1=ROM visible at $FFC0-$FFFF, 0=RAM) |
| 5 | Clear Port2/3 input latches (auto-clears) |
| 4 | Clear Port0/1 input latches (auto-clears) |
| 2 | Timer 2 enable |
| 1 | Timer 1 enable |
| 0 | Timer 0 enable |

---

## I/O Port Communication

### Port Crossover Mechanism

Each port address has **two separate registers** — read and write are independent:

| SPC700 addr | SNES addr | SPC700 reads | SPC700 writes |
|---|---|---|---|
| $F4 | $2140 | What SNES wrote to $2140 | Read by SNES from $2140 |
| $F5 | $2141 | What SNES wrote to $2141 | Read by SNES from $2141 |
| $F6 | $2142 | What SNES wrote to $2142 | Read by SNES from $2142 |
| $F7 | $2143 | What SNES wrote to $2143 | Read by SNES from $2143 |

Each side reads what the **other** side wrote. Writing to a port does NOT
change what you read back from that same port — you always read the other
CPU's output.

### SNES-side register names (memmap.i65)

```
APUIO0 = $2140    ; Port 0
APUIO1 = $2141    ; Port 1
APUIO2 = $2142    ; Port 2
APUIO3 = $2143    ; Port 3
```

### Programming caution: 16-bit port write hazard

When writing a 16-bit value to adjacent ports (e.g., address to $2142/$2143),
the SNES writes the low byte first. If the SPC700 reads the ports between
the two writes, it sees a corrupted value (new low, old high). The official
manual (Chapter 9, Caution 10) warns about this for $2142/$2143 specifically.

The sd2snes code avoids this by using the handshake protocol — the SPC700
only reads ports after the SNES signals via PORT0.

---

## DSP Register Map

Accessed indirectly via $F2 (address) and $F3 (data) on the SPC700 side.
128 registers total ($00-$7F).

### Per-Voice Registers (×8 voices, voice N at $N0-$N9)

| Offset | Name | Description |
|---|---|---|
| $x0 | VOL(L) | Left channel volume (signed 8-bit) |
| $x1 | VOL(R) | Right channel volume (signed 8-bit) |
| $x2 | P(L) | Pitch low byte |
| $x3 | P(H) | Pitch high byte (14-bit total with P(L)) |
| $x4 | SRCN | Source number (0-255, indexes DIR table) |
| $x5 | ADSR(1) | D7=ADSR enable, D6-D4=decay rate, D3-D0=attack rate |
| $x6 | ADSR(2) | D7-D5=sustain level, D4-D0=sustain rate |
| $x7 | GAIN | Envelope control when ADSR disabled (D7 of ADSR1=0) |
| $x8 | ENVX | Current envelope value (read-only, updated by DSP) |
| $x9 | OUTX | Current sample output after envelope (read-only) |

### Global Registers

| Address | Name | Description |
|---|---|---|
| $0C | MVOL(L) | Main volume left (signed 8-bit) |
| $1C | MVOL(R) | Main volume right |
| $2C | EVOL(L) | Echo volume left |
| $3C | EVOL(R) | Echo volume right |
| $4C | **KON** | Key On — D0-D7 correspond to voices 0-7 |
| $5C | **KOF** | Key Off — D0-D7 correspond to voices 0-7 |
| $6C | **FLG** | Flags: D7=soft reset, D6=mute, D5=echo write disable, D4-D0=noise clock |
| $7C | ENDX | Source end block indicator (read-only, D0-D7 = voices) |
| $0D | EFB | Echo feedback volume (signed 8-bit) |
| $1D | — | Not used |
| $2D | PMON | Pitch modulation enable (D1-D7, voice 0 cannot be modulated) |
| $3D | NON | Noise enable (D0-D7) |
| $4D | EON | Echo enable (D0-D7) |
| $5D | DIR | Source directory base address (×$100 in SPC RAM) |
| $6D | ESA | Echo region start address (×$100 in SPC RAM) |
| $7D | EDL | Echo delay (D0-D3 only, ×16ms, 0=no echo buffer) |
| $0F-$7F | C0-C7 | 8-tap FIR echo filter coefficients (signed 8-bit each) |

### FLG register ($6C) detail

| Bits | Function |
|---|---|
| D7 | Soft reset (1=reset all voices, mute output) |
| D6 | Mute (1=mute all output) |
| D5 | Echo write disable (1=disable echo buffer writes) |
| D4-D0 | Noise frequency clock (0-31) |

**Important for SPC loading**: During upload, FLG should be set to $60
(mute + echo write disable) to prevent audio glitches. The sd2snes loader
(`spc_loader` blob) forces FLG=$60 before restoring DSP registers. The final
restore sets FLG to the value from the SPC file.

### KON register ($4C) caution

KON is write-only and edge-triggered — the DSP reads it once per sample
period and clears it internally. During SPC state restore, KON must be
written as $00 initially (to prevent voices from starting prematurely),
then set to the correct value only after all other state is restored.
The sd2snes code (`upload_dsp_regs`) forces KON=$00 during upload.

### Source Directory (DIR)

The DIR register ($5D) points to a table of 4-byte entries in SPC RAM:

```
DIR × $100 + SRCN × 4 + 0: Start Address low byte
DIR × $100 + SRCN × 4 + 1: Start Address high byte
DIR × $100 + SRCN × 4 + 2: Loop Start Address low byte
DIR × $100 + SRCN × 4 + 3: Loop Start Address high byte
```

---

## BRR (Bit Rate Reduction) Format

SNES audio samples use 4-bit ADPCM compression called BRR. Compression
ratio is 32:9 (16-bit PCM → 4-bit BRR + header overhead).

### Block Structure

Each BRR block is **9 bytes**: 1 header byte + 8 data bytes = 16 samples.

```
Byte 0 (header):  [RRRR][FF][L][E]
                   D7-D4  D3  D1 D0
                          D2

  RRRR = Range (0-12): left-shift amount for 4-bit samples
  FF   = Filter (0-3): prediction filter selection
  L    = Loop flag: 1 = loop point (sets ENDX, jumps to loop start addr)
  E    = End flag: 1 = last block in sample

Bytes 1-8: 16 × 4-bit samples (each byte = 2 samples, high nibble first)
```

### Decoding Formula

```
x = R + a·x₋₁ + b·x₋₂

R = [d] × 2^(range-15)     where d is the signed 4-bit sample (-8 to +7)
```

### Filter Coefficients

| Filter | a | b | Order |
|---|---|---|---|
| 0 | 0 | 0 | None (raw shifted data) |
| 1 | 0.9375 | 0 | 1st order |
| 2 | 1.90625 | -0.9375 | 2nd order |
| 3 | 1.796875 | -0.8125 | 3rd order |

Filters 1-3 use prediction from previous samples for better compression.

---

## IPL Boot Protocol (Data Transfer Procedure)

The 64-byte IPL ROM at $FFC0-$FFFF handles initial communication with the
SNES CPU. This is the protocol used by `spc_begin_upload`, `spc_upload_byte`,
`spc_next_upload`, and `spc_execute` in `spc700.a65`.

### Protocol Steps

**Step 1-3: Initial Handshake** → `spc_begin_upload`

```
SPC700 signals ready:  PORT0 = $AA, PORT1 = $BB
SNES waits for $BBAA at $2140-$2141
SNES writes:
  PORT2 ($2142) = target address low
  PORT3 ($2143) = target address high
  PORT1 ($2141) = non-zero (data transfer mode)
  PORT0 ($2140) = $CC
SNES waits for PORT0 echo ($CC)
```

**Step 4-5: Byte Transfer** → `spc_upload_byte`

```
For each byte:
  SNES writes:
    PORT1 ($2141) = data byte
    PORT0 ($2140) = counter (starts at $00, increments by 1)
  SNES waits for PORT0 echo (SPC700 writes back the counter value)
```

**Step 6: Change Address (New Block)** → `spc_next_upload`

```
SNES writes:
  PORT2 ($2142) = new address low
  PORT3 ($2143) = new address high
  PORT1 ($2141) = non-zero (data transfer mode)
  PORT0 ($2140) = (previous PORT0 + 2), must wrap to avoid 0
SNES waits for PORT0 echo
```

The +2 increment (vs +1 for data) signals the IPL to read a new address
from PORT2/3 instead of storing PORT1 as data.

**Step 7: Execute** → `spc_execute`

```
SNES writes:
  PORT2 ($2142) = execution address low
  PORT3 ($2143) = execution address high
  PORT1 ($2141) = $00 (execute mode, not data transfer)
  PORT0 ($2140) = (previous PORT0 + 2)
SNES waits for PORT0 echo
SPC700 jumps to the specified address
```

PORT1=$00 distinguishes "execute at address" from "transfer to address".

### Re-entering IPL

Uploaded SPC700 code can return to the IPL boot loader by jumping to $FFC0
(`jmp $ffc0`). The SNES-side code then performs another begin_upload/
next_upload handshake. All sd2snes SPC700 code blobs (`apu_ram_init_code`,
`spc_loader`, `spc_transfer`) end with `jmp $ffc0` for this reason.

---

## SPC700 CPU Registers

| Register | Size | Description |
|---|---|---|
| A | 8-bit | Accumulator (pairs with Y for 16-bit MUL/DIV: YA) |
| X | 8-bit | Index register (also divisor for DIV) |
| Y | 8-bit | Index register (also multiplicand for MUL) |
| SP | 8-bit | Stack pointer (always in page 1: $0100+SP) |
| PC | 16-bit | Program counter |
| PSW | 8-bit | Processor status word |

### PSW Flags

| Bit | Flag | Description |
|---|---|---|
| 7 | N | Negative |
| 6 | V | Overflow |
| 5 | P | Direct page select (0=$0000-$00FF, 1=$0100-$01FF) |
| 4 | B | Break (set by BRK instruction) |
| 3 | H | Half-carry (BCD operations) |
| 2 | I | Interrupt enable (not used on SNES — no IRQ source) |
| 1 | Z | Zero |
| 0 | C | Carry |

---

## sd2snes SPC Player Architecture

The sd2snes SPC player (`spcplay.a65`) loads `.spc` save state files,
which contain a complete snapshot of SPC700 state (64KB RAM + DSP registers
+ CPU registers). The loading process must carefully restore this state
without audio glitches.

### Loading Sequence (`spc700_load`)

1. **Disable NMI** — timing-critical transfers cannot be interrupted
2. **Upload DSP registers** (`upload_dsp_regs`):
   - Upload `spc_loader` code to $0002
   - Append SP, PC(hi), PC(lo), PSW from SPC header (pushed to SPC stack)
   - Append 128 DSP register values (with KON forced to $00, FLG forced to $E0)
   - Append peripheral register values ($F1 control, $F2/$F3 DSP addr/data)
   - Append RAM $00F8-$01FF
   - Execute `spc_loader` at $0002 (restores DSP regs, re-enters IPL)
3. **Upload high RAM** (`upload_high_ram`):
   - Upload `spc_transfer` code to $0002
   - Execute it — receives 63.5KB ($0200-$FFFF) via 4-byte interleaved
     burst transfer through all 4 I/O ports simultaneously
4. **Upload low RAM** (`upload_low_ram`):
   - Byte-by-byte upload of $0002-$00EF (page 0, avoiding peripheral regs)
5. **Restore CPU state** (`restore_final`):
   - Use instruction injection (`exec_instr`) to set A, X, Y, SP
   - Restore DSP FLG and KON to their correct values
   - Set up a `BRA $FE` loop at $F5/$F6 (SPC700 spins reading its own port)
   - Write final I/O port values
   - Restore $F2/$F3 (DSP address/data)
   - The SPC700 is now running the original program from the save state
6. **Re-enable NMI**

### Instruction Injection (`exec_instr`)

The `exec_instr` routine executes arbitrary SPC700 instructions by:
1. Writing a 1-3 byte instruction to PORT1-PORT3 ($2141-$2143)
2. Writing a NOP count to PORT0 ($2140) — the SPC700 `BRA` loop detects
   the change and executes the instruction
3. Precise timing via PHD/PLD cycles (66 cycles between critical writes)

This technique allows setting SPC700 registers (A, X, Y, SP) without
needing a dedicated code blob for each combination.

### Warm Boot Exit

When the user presses B to exit the SPC player:
1. Save SP to `SAVED_SP` (SRAM at $002AFB)
2. Set `WARM_SIGNATURE` ($FA50) + complement
3. Call `pop_window` (restore file browser tile buffers)
4. Call `backup_wram` (DMA 8KB $7E:0000 → SRAM $FF:2000)
5. Write `CMD_RESET` to MCU
6. Spin until MCU resets the SNES

The only way to stop the SPC700 audio engine is a full system reset via
the MCU. There is no "stop" command — the SPC700 runs autonomously once
started.

---

## SPC File Format

The `.spc` file format stores a complete SPC700 state snapshot:

| Offset | Size | Content |
|---|---|---|
| $0000 | 33 | Header: "SNES-SPC700 Sound File Data v0.30" |
| $0025 | 2 | PC (program counter) |
| $0027 | 1 | A register |
| $0028 | 1 | X register |
| $0029 | 1 | Y register |
| $002A | 1 | PSW (processor status word) |
| $002B | 1 | SP (stack pointer) |
| $002E | 32 | Song title |
| $004E | 32 | Game title |
| $006E | 16 | Dumper name |
| $007E | 32 | Comments |
| $00A9 | 1 | Song length (seconds) |
| $0100 | 65536 | SPC700 RAM (complete 64KB) |
| $10100 | 128 | DSP registers ($00-$7F) |
| $10200 | 64 | Extra RAM (IPL ROM region, unused by most files) |

The sd2snes MCU loads the `.spc` file into SRAM where the SNES can read it
(SPC_HEADER at $FE0000 maps to offset $0000, SPC RAM at offset $0100 maps
to $FE0100-$FFFFFF).
