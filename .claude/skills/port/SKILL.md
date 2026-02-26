---
name: port
description: Guide for porting snescom assembly code to 64tass. Use when translating code between snes/ and snes-64tass/, or when hitting 64tass build errors.
argument-hint: "[filename.a65]"
---

# snescom → 64tass Porting Guide

Use this when translating code from `snes/` (snescom) to `snes-64tass/` (64tass).

## Syntax Conversion Table

| snescom | 64tass | Notes |
|---------|--------|-------|
| `#define FOO $1234` | `FOO = $1234` | Constants (no preprocessor) |
| `.byt $xx, $yy` | `.byte $xx, $yy` | Byte data |
| `.byt "text", 0` | `.text "text"` then `.byte 0` | String + null (or `.null "text"`) |
| `.word value` | `.word value` | Same |
| `@label` / `@$addr` | Auto-selected (24-bit if > $FFFF) | Long addressing |
| `!label` / `!$addr` | Auto-selected (16-bit if < $10000) | Absolute addressing |
| `#^label` | `#label >> 16` | Bank byte |
| `#!label` | `#label & $ffff` | 16-bit address portion |
| `.link page $C0` | `* = $C00000` | Set program counter |
| `sep #$20 : .as` | `sep #$20` newline `.as` | No `:` chaining |
| `rep #$10 : .xl` | `rep #$10` newline `.xl` | No `:` chaining |
| `- bra -` | `- bra -` | Same (anonymous labels work) |
| `jmp @label` | `jml label` | Long jump (or auto if cross-bank) |
| `inc` (accumulator) | `inc a` | 64tass requires explicit `a` operand |
| `dec` (accumulator) | `dec a` | 64tass requires explicit `a` operand |
| `mvn $7e, $c0` | `mvn $c0, $7e` | **Operand order reversed!** snescom=dst,src; 64tass=src,dst |
| `mvp $7e, $c0` | `mvp $c0, $7e` | Same reversal applies to MVP |

## Include Model

snescom uses a separate linker step (sneslink). 64tass is single-pass with `.include`:

```asm
; 64tass main.a65 — include everything, no linker needed
.cpu "65816"
.include "memmap.i65"      ; constants
.include "dma.i65"         ; macros
.include "data.i65"        ; WRAM variable addresses
* = $C00000                ; ROM start
; ... code ...
.include "ui.a65"          ; text renderer
.include "dma.a65"         ; HDMA setup
.include "font.a65"        ; font tile data
.include "palette.a65"     ; BGR555 palette
.include "const.a65"       ; HDMA tables, strings
.include "reset.a65"       ; NMI/IRQ handlers
.include "header.a65"      ; ROM header + vectors at $FFB0-$FFFF
.fill $C10000 - *, $00     ; pad to 64KB
```

**Include order matters**: define labels before referencing them. Put handler code (reset.a65) before header.a65 which references the vectors.

## Data Bank Tracking — The Big Difference

This is the most important difference from snescom. 64tass tracks the data bank register and **errors** when an absolute address doesn't match the current bank.

### Rules

1. **After RESET**: DBR=$00. Declare `.databank 0` at top of code.
2. **After `lda #$7e / pha / plb`**: Declare `.databank $7e`.
3. **In NMI/IRQ handlers**: Use `.databank ?` (DBR unknown at interrupt time).
4. **In subroutines**: Declare `.databank N` matching what the caller guarantees.

### Common Error: "not a data bank address"

```
main.a65:44:7: error: not a data bank address bits '$2121'
   stz $2121
       ^
```

**Cause**: The assembler thinks DBR != $00, but $2121 is a PPU register in bank $00.
**Fix**: Ensure `.databank 0` is active and runtime DBR is actually $00 at that point.

### PPU/CPU Registers Need Bank $00

PPU registers ($2100-$213F) and CPU registers ($4200-$43FF) ONLY exist in banks $00-$3F. Accessing them with DBR=$7E writes to WRAM, not hardware!

**Pattern**: Do all hardware register init while DBR=$00, then switch to $7E for WRAM:

```asm
GAME_MAIN
  sep #$20
  .as
  .databank 0           ; DBR=$00 from RESET
  stz $4200             ; CPU register — works with DBR=$00
  jsr snes_init         ; all PPU init — works with DBR=$00
  lda #$0f
  sta $2100             ; PPU register — works with DBR=$00
  ; NOW switch to $7E for WRAM access
  lda #$7e
  pha
  plb
  .databank $7e
  stz some_wram_var     ; $7E0027 — works with DBR=$7E
```

### NMI Handler — Long Addressing

NMI fires with unknown DBR. Two strategies:

**Strategy A** — Set DBR=$00 for register access, use long addressing for WRAM:
```asm
.databank ?
NMI_ROUTINE
  sep #$20
  .as
  lda #$00
  pha
  plb
  .databank 0
  sta $2115             ; PPU register — absolute (bank $00)
  lda $7E0025           ; WRAM variable — long addressing (auto-selected)
  lda #$01
  sta $7E0020           ; long store to WRAM
  rtl
```

Note: `stz` has NO long addressing mode. In NMI with `.databank 0`, use `lda #0 / sta $7Exxxx` instead.

**Strategy B** — Set DBR=$7E, use long addressing for registers:
```asm
  lda #$7e
  pha
  plb
  .databank $7e
  lda isr_done          ; absolute — assembler picks $0020
  sta $002100           ; long addressing for PPU register
```

Our NMI uses Strategy A (DBR=$00) since there are more register writes than WRAM writes.

## Macro Conversion

**Label placement**: Labels go BEFORE directives in 64tass:
```asm
; CORRECT:
AllocStack .macro
  ; ...
.endm

StackParam .function offset
  = _locals + offset + $05
.endf                          ; use .endf, NOT .endfunction

; WRONG — "label required" error:
.macro AllocStack
```

```asm
; snescom (cpp macros via #define):
; DMA7 #$01, src, $2118, #size
; (expanded by preprocessor)

; 64tass:
.macro DMA7 mode, src, dest, size
  lda #\mode
  sta $4370
  lda #\dest
  sta $4371
  ldx #\src & $ffff
  stx $4372
  lda #\src >> 16
  sta $4374
  ldx #\size
  stx $4375
  lda #$80
  sta $420b
.endm
```

## Vector Table

Labels are 24-bit in 64tass. Interrupt vectors are 16-bit `.word` entries:

```asm
* = $C0FFE4
  .word NMI_handler & $ffff    ; mask to 16-bit
  .word RESET & $ffff
  .word IRQ_handler & $ffff
```

## ROM Padding

64tass doesn't auto-pad. Explicitly fill to target size:

```asm
.if * < $C10000
  .fill $C10000 - *, $00       ; pad to exactly 64KB
.endif
```

## Porting Workflow

When porting a file from `snes/foo.a65` to `snes-64tass/foo.a65`:

1. Copy the file
2. Convert `#define` → constant assignments
3. Convert `.byt` → `.byte`, string handling
4. Remove `:` chaining (separate into newlines)
5. Replace `@` / `!` / `^` address prefixes
6. Replace `.link page` with `* =` addressing
7. Add `.databank` and `.dpage` directives matching runtime state
8. Ensure EVERY function has its own `.databank`/`.dpage` (they're global state!)
9. Add `.include` in main.a65 (no separate linker)
10. Build and fix any remaining errors
11. Compare behavior in bsnes against snescom version

## Porting Gotchas (Lessons Learned)

### .databank and .dpage state persists across labels (CRITICAL)
64tass `.databank` and `.dpage` are **global assembler state** — they do NOT reset at function boundaries. After `hiprint` sets `.databank ?` / `.dpage ?`, ALL subsequent functions in the same file inherit that unknown state and will error on absolute addressing.

**Rule**: Every function must redeclare `.databank` and `.dpage` at its entry:
```asm
my_function
  .databank 0
  .dpage 0
  sep #$20
  .as
  ; ... code using WRAM vars works now ...
```

### MVN/MVP operand order is REVERSED vs snescom — CRITICAL
snescom: `mvn destination, source` (WDC manual convention)
64tass: `mvn source, destination` (reversed!)

When porting `mvn $7e, $c0` from snescom (copy ROM $C0 → WRAM $7E), write `mvn $c0, $7e` in 64tass.

**Verify with binary**: Correct encoding for ROM→WRAM is `54 7E C0` (WDC byte order: dst=$7E, src=$C0). If you see `54 C0 7E`, the banks are swapped and the copy goes the wrong way.

**Failure mode**: Silently copies zeros from WRAM to read-only ROM. WRAM routines remain all zeros → JSL to WRAM executes BRK instructions → system crash. Only visible on real hardware since emulator mode never calls WRAM routines.

### MVN changes DBR — declare .databank after it
After `mvn $c0, $7e` in 64tass, DBR=$7E (destination bank). Use `.databank $7e` (not `.databank ?`) so `dec window_h` etc. validate correctly. Stack-relative ops (`lda $07,s`) don't use DBR so they work regardless.

### ROM constant access from .databank 0
With `.databank 0`, labels in bank $C0 (ROM) auto-select long (4-byte) addressing due to bank mismatch. WRAM vars at $00xx use absolute (2-byte) since they match bank $00. This is correct for HiROM.

### AllocStack DP conflict — avoid stack-allocated locals
When `AllocStack` sets DP dynamically via `TCD`, 64tass can't distinguish DP-relative locals ($00-$03) from absolute WRAM vars ($0040-$00FF). snescom uses `!` to force absolute — 64tass has no equivalent. **Solution**: use WRAM scratch variables (window_tmp, print_temp) instead.

### .xl/.xs MUST be declared in every function (CRITICAL)
64tass does NOT propagate register size state across `jsr`/`rts` boundaries or `jml` targets. If a function uses 16-bit index registers, it MUST declare `.xl` (and ideally `rep #$10`) at its entry — even if the caller already set 16-bit mode.

**Symptom**: Code silently generates 2-byte `ldy #imm` / `cpy #imm` instead of 3-byte. At runtime with 16-bit Y, the CPU eats an extra byte, misaligning ALL subsequent instructions. The function executes garbage and crashes or produces wrong output.

**Rule**: Start every function with explicit mode declarations:
```asm
my_function
  sep #$20
  .as
  rep #$10
  .xl
```

The same applies to `.as`/`.al` for accumulator immediates (`lda #imm`, `cmp #imm`, `adc #imm`). Any function using these must have the correct `.as` or `.al` in effect.

**How to verify**: Generate labels with `64tass --labels=labels.txt`, then hexdump the binary at the function address. Check that `LDY #nn` (opcode $A0) and `LDX #nn` (opcode $A2) have the right operand size (2 bytes for `.xs`, 3 bytes for `.xl`).

### .dpage 0 MUST be declared for indirect long addressing
64tass needs `.dpage 0` to correctly generate operand bytes for `[dp],y` (indirect long) addressing mode. Without it, the assembler may generate wrong DP offsets, causing reads from wrong memory locations.

**Symptom**: `lda [ptr],y` reads garbage instead of the data at the pointer. The code runs without errors but produces wrong values. Very hard to diagnose because the opcode looks correct in a disassembler — only the operand byte is wrong.

**Rule**: Add `.dpage 0` once near the top of main.a65, after `* = $C00000`:
```asm
* = $C00000
.dpage 0              ; DP is always $0000 (never changed after RESET)
```

This is safe because the SNES never changes the D register in our code. If you ever use `TCD` to change DP, update `.dpage` accordingly.

### Hidden B register corrupts TAX/TAY in mixed mode (M=1, X=0) — CRITICAL
The 65816 accumulator is always 16-bit internally (C = B:A). With 8-bit A (`sep #$20`), only the low byte (A) is visible. The high byte (B) is **hidden but persistent** — no 8-bit operation ever clears it, and it survives across `jsr`/`rts`, `php`/`plp`, and even NMI interrupts.

**The trap**: `TAX` and `TAY` with 16-bit index (X=0) transfer the **full 16-bit C** — including the stale B byte — into the index register. This silently corrupts the high byte of X or Y.

**Common sources of stale B**: `xba` (pad.a65 uses this), any prior 16-bit accumulator operation followed by `sep #$20`, or return from functions that used 16-bit A mode.

**Bug example**: `read_pad` uses `xba` to unpack joypad bits, leaving B=$08. This leaks through `update_ball` into `animate_gradient`, where `tax` produces X=$0800 instead of X=$0000. The gradient reads garbage palette offsets and transitions break.

**Fix**: Zero-extend through 16-bit mode before any TAX/TAY in mixed mode:
```asm
  ; A = 8-bit value, B = unknown garbage
  rep #$20
  .al
  and #$00ff            ; clear hidden B
  tax                   ; X = $00:value — safe
  sep #$20
  .as
```

**Rule**: Every `tax`/`tay` in .as/.xl mode needs B to be verified clean. See [Mixed-Mode Transfers reference](../snes-ref/reference/mixed-mode-transfers.md) for full details, audit checklist, and all safe patterns.

### WRAM buffer labels are already 24-bit
Labels like `BG1_TILE_BUF = $7EB000` in memmap.i65 are full addresses. Do NOT add `$7E0000 +` when using them as DMA source. `DMA7 $01, BG1_TILE_BUF, $18, $1000` is correct.

### OAM must be moved off-screen, not just cleared
DMA-clearing OAM to zeros puts 128 sprites at position (0,0) with tile 0 — they're visible! Either disable the OBJ layer (`$212C`/`$212D` = `$03` instead of `$13`) or set all sprite Y coordinates to $F0+ (off-screen).

### Color math window needs explicit disable
When the selection bar is hidden (bar_wl=0), the NMI's bar position math produces a small window at the screen edge. Add a check: if bar_wl=0, set window left > right ($2126=1, $2127=0) to disable the window entirely.

### WRAM variable area must be cleared
Low WRAM ($7E:0000-$7E:00FF) must be DMA-cleared at boot. Uninitialized bar_xl/bar_wl produce visible color math artifacts. But do NOT clear past $7E:00FF — the stack lives at $1FFF and clearing it inside a JSR wipes the return address (black screen).

### VRAM must be explicitly cleared
Unlike snescom which may have implicit clearing, 64tass builds need explicit DMA fills to zero VRAM regions. Random tile data renders as garbage characters.

### AllocStack → WRAM locals: recursion needs manual save/restore (CRITICAL)
snescom's `AllocStack` creates a new stack frame per call, so recursive functions like `show_menu` get isolated locals automatically. In 64tass, we replace AllocStack with WRAM variables — but these are shared globals, so recursive calls overwrite the parent's values.

**Solution**: Save WRAM locals to the hardware stack before the recursive call, restore after. Use the `PushMenuLocals` / `PopMenuLocals` macros in menu.a65 to enforce correct order and width.

**LIFO cleanliness rule**: Any register you intend to restore with `pl?` must be the **last thing pushed** before the bracketed call. Either:
- Save locals → `phy` → call → `ply` → restore locals, or
- `phy` → call → `ply` with nothing else pushed between.

If locals sit between `phy` and `ply`, the `ply` pops wrong data:
```asm
; WRONG — ply pops saved locals instead of Y:
phy
  lda sm_numentries : pha    ; 7 bytes between phy and ply!
  jsr push_window
ply                          ; BUG: pops sm_menu_ptr bytes, not Y

; CORRECT — locals below Y on stack, bracket is clean:
PushMenuLocals               ; save locals first (enforces .as/.al widths)
phy                          ; then push Y
  jsr push_window
ply                          ; correctly pops Y
; ... recursive call ...
PopMenuLocals                ; restore locals (enforces matching widths)
```

**Width trap**: `pha`/`pla` push/pop 1 byte in `.as` and 2 bytes in `.al`. All save/restore blocks must enforce the same A width on save and restore. The macros handle this — if writing by hand, always `sep #$20` before 1-byte locals and `rep #$20` before 2-byte locals.

### `#<label` low-byte operator in 16-bit register loads (CRITICAL)
In 64tass, `<` is the low-byte operator (bits 0-7). The expression `#<label & $ffff` parses as `(<label) & $ffff` = just the low byte, NOT the full 16-bit address. This is different from snescom's `#^label` / `#!label` convention.

**Symptom**: 16-bit register X or Y gets `$00xx` instead of the correct `$xxxx` address. Pointers are wrong, menu structures read garbage, windows are mis-sized.

**Fix**: For 16-bit address loads, use explicit parentheses — no `<`:
```asm
; WRONG — loads only low byte:
ldx #<menu_enttab_mm & $ffff    ; X = $00xx

; CORRECT — loads full 16-bit address (parens for clarity):
ldx #((menu_enttab_mm) & $ffff) ; X = $xxxx
```

For bank byte loads, use the same parenthesized style for consistency:
```asm
lda #((label >> 16) & $ff)      ; bank byte — unambiguous
```

### Stack parameter offsets shift when extra pushes are added
When converting functions that pass parameters on the stack, any extra `phb`/`pha` between the parameter pushes and the `jsr` call shifts all stack-relative offsets.

**Example**: `_show_menu_entries` pushes max_lbl_len and max_opt_len, then does `phb` to switch DBR before `jsr menu_print_entries`. The extra `phb` adds 1 byte, so inside `menu_print_entries`:
```asm
; Without phb: P_MAX_OPT_LEN = 3, P_MAX_LBL_LEN = 4
; With phb:    P_MAX_OPT_LEN = 4, P_MAX_LBL_LEN = 5
;              (each offset +1 for the extra byte on stack)
```

**Rule**: Count ALL bytes on the stack between `jsr` and the parameters. Return address (2) + any intervening pushes = base offset. Whenever a function pushes additional bytes before `jsr`, update the callee's `P_*` offset constants. Consider passing via registers or WRAM instead of stack params when the offset math gets fragile.

### Processor mode mismatch across subroutine returns (CRITICAL)
When a called function changes processor mode (.as↔.al, .xs↔.xl) and returns without restoring it, the assembler's tracked state diverges from the actual CPU state. The assembler generates wrong-sized immediates.

**Example**: `menu_print_opt_string` starts with `sep #$20 / .as` and returns in `.as` mode. The caller's assembler state still says `.al`, so `adc #MENU_ENTRY_SIZE` generates a 3-byte immediate. But the CPU is in 8-bit mode and reads only 2 bytes — the stray `$00` executes as BRK → crash.

**Rule**: Every subroutine must either **(A)** preserve M/X flags on return (via `php`/`plp`), or **(B)** document the mode it returns in. Callers must then `rep`/`sep` + `.al`/`.as`/`.xl`/`.xs` accordingly. This applies to **both** A width and X/Y width — people fix A and forget indexes.

```asm
jsr menu_print_opt_string    ; returns in .as mode (documented)
rep #$20                     ; explicitly restore 16-bit A
.al                          ; tell assembler
txa
clc
adc #MENU_ENTRY_SIZE         ; now correctly generates 3-byte immediate
```

### `.databank ?` rejects literal address offsets
With `.databank ?`, 64tass errors on absolute-mode literal addresses like `lda $0001, x` — it can't validate the bank. With `.databank $C0`, small addresses ($0000-$00FF) still fail because they look like DP.

**Fix**: Use `.databank 0` (lie) for functions where DBR = menu bank at runtime but you need `$N,x` indexed access to menu structures. Bank $00 has WRAM labels covering the low address range, so 64tass accepts the addresses. The machine code is identical — `.databank` only affects assembler validation, not output.

**Warning**: `.databank 0` can hide real bugs if DBR is not what you expect at runtime. Only use it when the invariant is documented: "DBR = menu bank when executing these indexed reads."

Toggle `.dpage ?` around the indexed access to force absolute mode (prevent DP optimization):
```asm
.databank 0    ; invariant: DBR = menu bank at runtime
.dpage ?
lda $0001, x         ; forced to absolute indexed mode
lda $0007, x
.dpage 0              ; restore for normal DP access
```

### PHA/PLA symmetry depends on A width
`pha`/`pla` push/pop 1 byte in `.as` and 2 bytes in `.al`. If a save block pushes in `.as` but the restore pops in `.al` (or vice versa), the stack silently misaligns. Every save/restore sequence must enforce matching widths — use `sep #$20` / `rep #$20` explicitly around each group rather than relying on inherited state.

### NMI stack budget assumption
NMI and IRQ handlers push to the same hardware stack as menu recursion and save/restore sequences. The system is safe because: (1) the NMI handler has a bounded, fixed stack budget (no recursion), and (2) menu recursion depth is bounded by the menu structure (max ~3 levels). If either assumption changes, audit stack depth.

## Port Status

### Milestone 1 — Boot to screen (COMPLETE)
| File | Status | Notes |
|------|--------|-------|
| memmap.i65 | Done | 177 constants converted |
| dma.i65 | Done | DMA7 macro converted |
| header.a65 | Done | Vectors use `& $ffff` |
| reset.a65 | Done | Minimal NMI stub, `.databank ?` |
| main.a65 | Done | Boot, snes_init, VRAM/CGRAM clear |

### Milestone 2 — Gradient + text (COMPLETE)
| File | Status | Notes |
|------|--------|-------|
| data.i65 | Done | WRAM variable addresses as `$7E`-prefixed constants |
| ui.a65 | Done | hiprint Mode 5 text renderer, `.databank $7e` |
| dma.a65 | Done | HDMA setup (6 channels), killdma |
| font.a65 | Done | 4096 bytes 2bpp tile data (`.byt` → `.byte`) |
| palette.a65 | Done | 512 bytes BGR555 palette |
| const.a65 | Done | HDMA tables, gradient, strings |
| reset.a65 | Expanded | Full NMI: tile DMA, bar positioning, brightness fade |
| main.a65 | Expanded | setup_gfx, genfonts, video_init, poc_display, emu_mode |

### Milestone 3 — Input + sprites + UI building blocks (COMPLETE)
| File | Status | Notes |
|------|--------|-------|
| pad.a65 | Done | All 12 buttons, edge detection |
| OAM/sprites | Done | Bouncing ball sprite demo |
| stack.i65 | Done | AllocStack/FreeStack macros |
| common.a65 | Done | strlen, bin2dec16 utilities |
| ui.a65 | Done | All 12 functions: hiprint, loprint, draw_window, push/pop_window, window_greyout, hide_cursor, right_align, set_bar_color, draw_loading_window, disable/enable_screen_update |
| data.i65 | Expanded | Window, list selector, filesel WRAM vars |
| const.a65 | Expanded | Window frame chars, space64, loading data |

### Milestone 4 — File browser + MCU (COMPLETE)
| File | Status | Notes |
|------|--------|-------|
| filesel.a65 | Done | Full file browser: init, loop, dir rendering, nav, MCU comms |
| time.a65 | Done | Clock: gettime, rendertime, printtime, settime, rtc_init, time_init |
| main.a65 | Expanded | WRAM routines, store_wram_routines, wait_mcu_ready, game_handshake, MCU boot path |
| data.i65 | Expanded | Time/RTC vars ($02A0-$02B0), work vars, infloop, mm_tmp/sel |
| const.a65 | Expanded | Clock dialog strings/dims, text_ellipse |
| menu_select | Done | Ported into filesel.a65 (Mode 7 multiply, selection loop) |

### Milestone 5 — Menu system (IN PROGRESS)
| File | Status | Notes |
|------|--------|-------|
| menu.a65 | Done | Full menu system: show_menu (recursive), measure, print, edit_value, all dialog types |
| menudata.a65 | Done | All menu tables: main, config, BSX, browser, chip, SGB, in-game, savestates, SCIC |
| sysinfo.a65 | Done | System info display |
| data.i65 | Expanded | Menu WRAM vars: sm_*, menu_val_ptr, menu_aux_ptr, mev_*, mpos_* |
| Known issues | — | Config value editing not yet working (under investigation) |
| Stubs remaining | — | spcplayer |
