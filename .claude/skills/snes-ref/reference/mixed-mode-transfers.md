# 65816 Mixed-Mode Register Transfers (Hidden B Register)

## The Problem

The 65816 accumulator is always 16-bit internally, called **C**, split into:
- **A** (low byte) — visible when M=1 (8-bit accumulator mode)
- **B** (high byte) — **invisible** when M=1, but still physically present

When M=1 (`sep #$20`, `.as`), 8-bit operations only touch A. B is never modified by:
- `lda` (8-bit load only writes A)
- `adc`, `sbc`, `and`, `ora`, `eor` (8-bit ALU only affects A)
- `inc a`, `dec a`, `asl a`, `lsr a`, `rol a`, `ror a`
- `sta` (8-bit store only reads A)

**B persists silently** across all of these. It also persists across:
- `jsr` / `rts` (subroutine calls don't save/restore A or B)
- `php` / `plp` (only saves/restores the P register, not the accumulator)
- NMI interrupts (the NMI handler saves and restores the full C, preserving B)

## Mixed-Mode Transfer Behavior

When M and X flags differ (most commonly **M=1 / X=0** — 8-bit A with 16-bit index), the inter-register transfers behave as follows:

| Instruction | M=1, X=0 behavior | Danger |
|-------------|-------------------|--------|
| **`TAX`** | X ← full 16-bit C (both B:A) | **B contaminates X high byte** |
| **`TAY`** | Y ← full 16-bit C (both B:A) | **B contaminates Y high byte** |
| `TXA` | A ← X low byte; B ← X high byte | B is overwritten (may be useful or harmful) |
| `TYA` | A ← Y low byte; B ← Y high byte | B is overwritten (may be useful or harmful) |

### Key rule: `TAX` and `TAY` always transfer based on the **destination** register's size

With X=0 (16-bit index), `TAX`/`TAY` transfer all 16 bits of C, regardless of the M flag. The M flag only controls which byte is "visible" for accumulator operations — it does NOT prevent the full 16-bit transfer.

## The Dangerous Pattern

```asm
sep #$20        ; 8-bit A (M=1)
rep #$10        ; 16-bit X/Y (X=0) — very common in this codebase
; ... some 8-bit work, maybe calling other functions ...
lda some_byte   ; A = value (0-255), B = UNKNOWN GARBAGE
tax             ; X = (B << 8) | A — HIGH BYTE IS GARBAGE
lda table,x     ; reads from wrong offset!
sta destination  ; corrupted data written
```

## Real Bug: animate_gradient (this codebase)

`read_pad` contains `xba` to unpack the joypad high byte. This leaves B=$08 (the shifted low-byte result). The B byte leaked through `update_ball` (all 8-bit, never touches B) into `animate_gradient`, where:

```asm
  lda bounce_wall   ; 8-bit: A = 1-4, B = $08 (stale from read_pad's xba)
  dec a             ; A = 0-3, B still $08
  tax               ; X = $0800 + (0 to 3) — WRONG! Should be $0000 + (0 to 3)
  lda gradient_phase_offsets,x  ; reads from offset $0800+ instead of $0000+
```

Result: gradient transition reads garbage palette index, corrupting the animation. The gradient appears "stuck" — transitions triggered by ball bounces never display.

## Sources of Stale B Values

1. **`xba`** — explicitly swaps A and B. After `xba`, B contains what was in A.
2. **16-bit operation → `sep #$20`** — any 16-bit `lda`, `adc`, etc. sets the full C. When you switch to 8-bit mode, the high byte becomes B.
3. **`txa` / `tya`** — when M=1 and X=0, these set B to the source register's high byte.
4. **Previous function calls** — if any called function uses `xba` or 16-bit A, B may be non-zero on return. `php`/`plp` does NOT clear B.
5. **Cross-frame persistence** — B survives across the entire mainloop. A stale B from frame N affects frame N+1, N+2, etc.

## Safe Patterns

### Pattern 1: Zero-extend through 16-bit mode (RECOMMENDED)

```asm
; Before: A = 8-bit value, B = unknown
  rep #$20
  .al
  and #$00ff        ; clear high byte (B → 0)
  tax               ; X = $00:value — safe
  sep #$20
  .as
```

This is the clearest and most defensive pattern. Use it wherever you need TAX/TAY in mixed mode.

### Pattern 2: Full 16-bit load before transfer

```asm
; Load a full 16-bit value that naturally zeroes the high byte
  rep #$20
  .al
  lda some_word     ; overwrites both A and B
  tax               ; clean transfer
  sep #$20
  .as
```

Only works when you have a 16-bit source. Not applicable for 8-bit byte → index transfers.

### Pattern 3: Clear B explicitly (compact but tricky)

```asm
; Before: A = 8-bit value, B = unknown
  xba               ; swap: A = old B, B = old A (value we want)
  lda #$00          ; A = 0
  xba               ; swap back: A = our value, B = 0
  tax               ; X = $00:value — safe
```

This is 4 bytes vs 5 for pattern 1. Use when code size matters, but pattern 1 is clearer.

## Audit Checklist

When writing or reviewing 65816 code with mixed register sizes (M=1, X=0):

- [ ] **Search for `tax` and `tay`** — every instance in .as/.xl mode is suspect
- [ ] **Trace B's value** — follow the accumulator backwards to the last 16-bit operation, `xba`, `txa`, `tya`, or function call
- [ ] **Check function call chains** — if you call any function before the `tax`/`tay`, B could be anything
- [ ] **Especially after `xba`** — the most common source of stale B in this codebase (pad.a65 uses it)
- [ ] **`txa` and `tya` in 8-bit mode** — these SET B to the source's high byte, which may affect later `tax`/`tay`

## Additional Notes

- The M=1/X=1 case (both 8-bit) is safe: `TAX`/`TAY` only transfer 8 bits, and X/Y high bytes are forced to $00.
- The M=0/X=0 case (both 16-bit) is safe: full 16-bit transfers are always clean.
- The M=0/X=1 case (16-bit A, 8-bit index) is unusual but: `TAX`/`TAY` transfer only the low byte of A to the 8-bit index register. This truncates but doesn't corrupt.
- The **dangerous case is always M=1/X=0** (8-bit A, 16-bit index), which is the most common mixed mode in SNES programming.
