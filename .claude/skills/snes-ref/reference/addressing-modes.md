# 65816 Addressing Modes (snescom syntax)

## Immediate
- `lda #$42` - 8-bit immediate (when .as)
- `lda #$1234` - 16-bit immediate (when .al)
- `ldx #$00` / `ldx #$1234` - depends on .xs/.xl

## Direct Page (DP)
- `lda $42` - DP (8-bit address, DP-relative)
- `lda ($42)` - DP indirect
- `lda [$42]` - DP indirect long (24-bit pointer)
- `lda ($42,x)` - DP indexed indirect
- `lda ($42),y` - DP indirect indexed
- `lda [$42],y` - DP indirect long indexed

## Absolute
- `lda !$1234` or `lda $1234` - absolute (16-bit, current data bank)
- `lda !$1234,x` - absolute indexed X
- `lda !$1234,y` - absolute indexed Y
- `lda ($1234)` - absolute indirect (JMP only)
- `lda ($1234,x)` - absolute indexed indirect (JMP/JSR)

## Long
- `lda @$7E1234` - long (24-bit absolute)
- `lda @$7E1234,x` - long indexed
- `jsl @$7EF000` - long subroutine call

## snescom Label Syntax
- `#!label` - immediate 16-bit address of label
- `#^label` - immediate bank byte of label
- `@label` - long address of label
- `!label` - absolute (16-bit) address of label

## Block Move
- `mvn dest_bank, src_bank` - block move next
  - X = source, Y = destination, A = count-1
  - Moves bytes, decrements after each

## Stack
- `lda $03,s` - stack relative
- `lda ($03,s),y` - stack relative indirect indexed

## Relative (branches)
- `bra label` - always branch (8-bit offset, +/-128 bytes)
- `brl label` - long branch (16-bit offset)
- `beq/bne/bcs/bcc/bmi/bpl/bvs/bvc` - conditional (8-bit offset)
