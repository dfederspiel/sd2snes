# SNES Hardware Multiply & Divide Reference

Source: Nintendo SNES Development Manual, Book I — Chapter 15 (Absolute Multiplication/Division), Chapter 28 (Register Definitions $4202-$4206, $4214-$4217).

## Overview

The SNES CPU provides hardware-accelerated **unsigned** integer math via I/O registers:
- **Multiply**: 8-bit x 8-bit = 16-bit product
- **Divide**: 16-bit / 8-bit = 16-bit quotient + 16-bit remainder

These are CPU registers ($42xx), not PPU registers — accessible from any bank with DBR=$00-$3F.

## Registers

### Write Registers

| Register | Name | Purpose |
|----------|------|---------|
| $4202 | WRMPYA | Multiplicand A (8-bit unsigned) |
| $4203 | WRMPYB | Multiplier B (8-bit unsigned) — **triggers multiply** |
| $4204 | WRDIVL | Dividend C low byte (16-bit unsigned, low) |
| $4205 | WRDIVH | Dividend C high byte (16-bit unsigned, high) |
| $4206 | WRDIVB | Divisor B (8-bit unsigned) — **triggers divide** |

### Read Registers

| Register | Name | Purpose |
|----------|------|---------|
| $4214 | RDDIVL | Division quotient low byte |
| $4215 | RDDIVH | Division quotient high byte |
| $4216 | RDMPYL | **Dual-purpose**: multiply product low / divide remainder low |
| $4217 | RDMPYH | **Dual-purpose**: multiply product high / divide remainder high |

**Critical**: $4216/$4217 hold the multiply product OR the divide remainder, depending on which operation ran last.

All registers initialize to $00 at power-on.

## Multiplication

### Sequence

1. Write multiplicand A to `$4202`
2. Write multiplier B to `$4203` — **starts the multiply immediately**
3. **Wait 8 machine cycles**
4. Read 16-bit product from `$4216` (low) / `$4217` (high)

### Timing

The operation completes 8 machine cycles after the write to $4203. At 2.68 MHz (slow ROM), 8 machine cycles = 8 clock ticks. In practice, the instructions between the $4203 write and the $4216 read must consume at least 8 cycles.

**Cycle-burning patterns** (each instruction's cycle count is for 2.68 MHz slow bus):

```
; Pattern 1: NOP chain (2 cycles each)
nop         ; 2
nop         ; 4
nop         ; 6
nop         ; 8

; Pattern 2: pha/pla (compact)
pha : pla   ; 7 cycles (3+4)
nop         ; 2 = 9 (safe margin)

; Pattern 3: dummy register read
lda $4212   ; 4 cycles (absolute read)
lda $4212   ; 4 cycles = 8 total
```

### Example: 8x8 Multiply

```asm
; Compute 25 * 10 = 250 ($FA)
  sep #$20 : .as
  lda #25
  sta $4202       ; multiplicand = 25
  lda #10
  sta $4203       ; multiplier = 10, starts operation
  nop             ; 2
  nop             ; 4
  nop             ; 6
  nop             ; 8 cycles elapsed
  rep #$20 : .al
  lda $4216       ; A = $00FA (250)
```

## Division

### Sequence

1. Write dividend C low byte to `$4204`
2. Write dividend C high byte to `$4205`
3. Write divisor B to `$4206` — **starts the divide immediately**
4. **Wait 16 machine cycles**
5. Read 16-bit quotient from `$4214` (low) / `$4215` (high)
6. Read 16-bit remainder from `$4216` (low) / `$4217` (high)

### Timing

16 machine cycles — twice as long as multiply. The cycle-burning code must be more substantial.

### Divide-by-Zero Behavior

If divisor B = 0:
- Quotient ($4214/$4215) = **$FFFF**
- Remainder ($4216/$4217) = the original dividend C

No exception or interrupt is generated. The CPU silently returns $FFFF.

### Example: 16-bit / 8-bit Division

```asm
; Compute 1000 / 10 = 100 remainder 0
  sep #$20 : .as
  rep #$10 : .xl
  ldx #1000         ; dividend
  stx $4204         ; writes low ($E8) and high ($03)
  lda #10
  sta $4206         ; divisor = 10, starts operation
  ; burn 16 cycles:
  pha : pla          ; 7 (3+4)
  pha : pla          ; 7 = 14
  nop                ; 2 = 16
  rep #$20 : .al
  lda $4214          ; quotient = 100 ($0064)
  ldx $4216          ; remainder = 0 ($0000)
```

## Codebase Usage: bin2dec16 (common.a65)

The `bin2dec16` routine converts a 16-bit number to decimal ASCII using repeated division by 10:

```asm
bin2dec16:
  ; A = 16-bit value to convert
  ; Uses hardware divide in a loop:
-   sta $4204         ; store dividend (quotient from previous iteration)
    lda #$000a
    sta $4206         ; divisor = 10, starts divide
    pha : pla         ; 7 cycles
    xba               ; 3 cycles = 10
    lda @$004216      ; 5 cycles (long read) = 15... + 1 from sta above
    ; remainder (0-9) → convert to ASCII, store in buffer
    ora #$30          ; ASCII '0' = $30
    tay
    sty stringbuf, x
    dex
    lda $4214         ; load quotient for next iteration
    beq +             ; done when quotient = 0
    bra -
```

**Key details**:
- Uses `rep #$20` (16-bit A) so `sta $4204` writes both $4204 and $4205 in one instruction
- The long-address form `lda @$004216` is used because DBR may not be $00
- Cycle burn: `pha:pla` (7) + `xba` (3) + `lda @$004216` (5) = 15 cycles after `sta $4206` (the `sta` itself provides at least 1 more). Well over the 16-cycle minimum.

## Complementary (Signed) Multiplication

The SNES has a **separate** signed multiply using PPU Mode 7 registers — NOT the $4202/$4203 registers:

| Register | Purpose |
|----------|---------|
| $211B | M7A — 16-bit signed multiplicand (write-twice: low then high) |
| $211C | M7B — 8-bit signed multiplier (also starts the multiply) |
| $2134-$2136 | 24-bit signed product (read: low, mid, high) |

This is a 16x8→24 signed multiply with **no wait cycles** — the result is available immediately. It's primarily used for Mode 7 rotation matrix math but can be repurposed for any signed multiplication.

**Gotcha**: Writing to $211B/$211C also affects Mode 7 matrix parameters A and B. If using Mode 7 for display, save/restore these registers.

## Signed Math with Unsigned Registers

The $4202/$4203 registers only do unsigned math. For signed operations:

### Signed 8x8 Multiply Pattern

```asm
; Signed multiply: result in A (16-bit)
; Inputs: value1 in A (8-bit signed), value2 in some register
  ; 1. Record sign: XOR the sign bits
  ; 2. Take absolute values
  ; 3. Unsigned multiply
  ; 4. Negate result if signs differed
```

### Right-Shift for Division by Powers of 2

For dividing by 2/4/8/16, bit shifting is faster than hardware divide:

```asm
; Unsigned: A >> 1 = A / 2
  lsr

; Signed (16-bit): arithmetic right shift
  cmp #$8000        ; set carry = sign bit
  ror               ; rotate right through carry (preserves sign)
```

## Quick Reference

| Operation | Write | Trigger | Wait | Read |
|-----------|-------|---------|------|------|
| A * B | $4202=A | $4203=B | 8 cycles | $4216/$4217 = product |
| C / B | $4204/$4205=C | $4206=B | 16 cycles | $4214/$4215=quotient, $4216/$4217=remainder |
| A * B (signed) | $211B=A (16-bit) | $211C=B (8-bit) | 0 cycles | $2134-$2136 = 24-bit product |

**Register preservation**: $4202 (multiplicand) and $4204/$4205 (dividend) are **not destroyed** by the operation — safe to read back or reuse without rewriting.
