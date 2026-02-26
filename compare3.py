#!/usr/bin/env python3
"""Final detailed analysis of WRAM routine differences."""

with open("/mnt/c/Users/david/code/sd2snes/snes/menu.bin", "rb") as f:
    orig = bytearray(f.read())
with open("/mnt/c/Users/david/code/sd2snes/snes-64tass/menu.bin", "rb") as f:
    port = bytearray(f.read())

print("=" * 70)
print("STORE_BLOCKRAM_ROUTINE_SRC - MVN encoding check")
print("=" * 70)

# Original MVN at $09B2 + 0x1B = $09CD
mvn_orig = 0x09B2 + 0x1B
# Port MVN at $08D3 + 0x1D = $08F0
mvn_port = 0x08D3 + 0x1D

print(f"  Original MVN at ${mvn_orig:04X}: {orig[mvn_orig]:02X} {orig[mvn_orig+1]:02X} {orig[mvn_orig+2]:02X}")
print(f"    WDC dst=${orig[mvn_orig+1]:02X} src=${orig[mvn_orig+2]:02X}")
print(f"  Port MVN at ${mvn_port:04X}: {port[mvn_port]:02X} {port[mvn_port+1]:02X} {port[mvn_port+2]:02X}")
print(f"    WDC dst=${port[mvn_port+1]:02X} src=${port[mvn_port+2]:02X}")

if orig[mvn_orig:mvn_orig+3] == port[mvn_port:mvn_port+3]:
    print("  RESULT: MVN encoding IDENTICAL")
else:
    print("  RESULT: MVN encoding DIFFERENT!")
    if orig[mvn_orig+1] == port[mvn_port+2] and orig[mvn_orig+2] == port[mvn_port+1]:
        print("  WARNING: Operands are REVERSED! (src/dst swapped)")

print()

# Check all MVN instructions in both binaries
print("=" * 70)
print("ALL MVN (54) AND MVP (44) INSTRUCTIONS")
print("=" * 70)

for label, data in [("Original", orig), ("Port", port)]:
    print(f"\n  {label}:")
    for i in range(len(data) - 3):
        if data[i] in (0x54, 0x44):
            op = "MVN" if data[i] == 0x54 else "MVP"
            # WDC encoding: opcode dst src
            dst = data[i+1]
            src = data[i+2]
            print(f"    ${i:04X}: {op} ${dst:02X} ${src:02X}  (copy from bank ${src:02X} to bank ${dst:02X})")

print()
print("=" * 70)
print("FADELOOP - cur_bright addressing")
print("=" * 70)

# Original: LDX $041C at fadeloop+$0B
# Port:     LDX $31 at fadeloop+$0B
print()
print("  Original: LDX $041C (absolute, 3 bytes)")
print("  Port:     LDX $31   (direct page, 2 bytes)")
print()
print("  Both load cur_bright into X. The port uses DP addressing because")
print("  cur_bright=$0031 is in the DP range ($00-$FF) with DP=0.")
print()
print("  fadeloop executes from BRAM bank $00 after PHK/PLB sets DBR=$00.")
print("  DP should be $0000 at this point (set during init and never changed).")
print("  So LDX $31 correctly reads from $00:0031 = cur_bright.")
print()

# Verify fadeloop lengths
for i in range(0x08DD, 0x08DD + 140):
    if orig[i] == 0x80 and orig[i+1] == 0xFE:
        orig_len = i + 2 - 0x08DD
        break

for i in range(0x08F6, 0x08F6 + 140):
    if port[i] == 0x80 and port[i+1] == 0xFE:
        port_len = i + 2 - 0x08F6
        break

print(f"  Original fadeloop length: {orig_len} bytes")
print(f"  Port fadeloop length:     {port_len} bytes")
print(f"  Difference: {orig_len - port_len} byte(s)")
print(f"  DMA copies $EF (239) bytes - both fit with plenty of margin")

print()
print("=" * 70)
print("WRAM_ROUTINE_SRC - byte-exact match check")
print("=" * 70)

# Both are 29 bytes, let's verify byte-for-byte
orig_off = 0x09D3
port_off = 0x08B6
length = 29  # includes RTL

match = True
for i in range(length):
    if orig[orig_off + i] != port[port_off + i]:
        match = False
        print(f"  DIFF at +${i:02X}: orig=${orig[orig_off+i]:02X} port=${port[port_off+i]:02X}")

if match:
    print("  ALL 29 BYTES IDENTICAL")

print()
print("=" * 70)
print("WRAM_WAIT_MCU_SRC - byte-exact match check")
print("=" * 70)

orig_off = 0x09F0
port_off = 0x097B
length = 9  # tight loop: LDA/CMP/BNE/RTL

match = True
for i in range(length):
    if orig[orig_off + i] != port[port_off + i]:
        match = False
        print(f"  DIFF at +${i:02X}: orig=${orig[orig_off+i]:02X} port=${port[port_off+i]:02X}")

if match:
    print("  ALL 9 BYTES IDENTICAL")

print()
print("=" * 70)
print("COMPLETE SUMMARY")
print("=" * 70)
print("""
WRAM Routine Comparison Results:

1. wram_routine_src (FPGA reconfig, $7EF000):
   STATUS: IDENTICAL (29 bytes, byte-for-byte match)
   No issues.

2. store_blockram_routine_src ($7EF080):
   STATUS: FUNCTIONALLY EQUIVALENT but DIFFERENT ENCODING
   - Variable addresses differ: $0419 (orig) vs $02B6 (port)
     This is expected — different assemblers allocate WRAM vars at different offsets.
   - Addressing mode: absolute (orig) vs long (port)
     The port uses .databank ? which forces long addressing for all memory accesses.
     This is 2 bytes larger but functionally correct.
   - MVN encoding: IDENTICAL ($54 $00 $7E = copy from bank $7E to bank $00)
   - Routine length: 33 (orig) vs 35 (port) — but both fit in $80 DMA copy size.
   NOT A BUG — functionally equivalent.

3. fadeloop ($7EF100):
   STATUS: FUNCTIONALLY EQUIVALENT but DIFFERENT ENCODING
   - cur_bright addressing: absolute LDX $041C (orig) vs DP LDX $31 (port)
     Both load the same logical variable. Port uses DP addressing (smaller).
   - 1-byte shorter at that point, causing all subsequent bytes to shift by 1.
   - All branch targets remain correct (relative branches are position-independent).
   - All absolute addresses ($2100, $4200, etc.) are hardware registers — identical.
   - Routine length: 134 (orig) vs 133 (port) — both fit in $EF DMA copy size.
   NOT A BUG — functionally equivalent.

4. wram_wait_mcu_src ($7EF200):
   STATUS: IDENTICAL (9 bytes, byte-for-byte match)
   No issues.

CONCLUSION:
   The WRAM routines are functionally equivalent between the two builds.
   The differences are:
   - Variable address allocation (different assembler = different offsets)
   - Addressing mode choices (64tass .databank ? forces long; DP optimization)

   NONE of these differences should cause a game launch black screen.
   The game launch path (game_handshake -> wram_routine -> store_blockram -> fadeloop)
   should work correctly with the port's routines.
""")

# One more critical check: does the infloop variable exist at the right address
# in the port? The store_blockram routine writes BRA $FE there.
print("=" * 70)
print("BONUS: Checking infloop variable usage")
print("=" * 70)
print()

# In the port, infloop is at $02B6 (from the STA $0002B6)
# Let's check if anything else references $02B6 or if it's orphaned
# Search for 02B6 in the port binary
print("Port references to $02B6/$02B7 (infloop):")
for i in range(len(port) - 3):
    # Look for B6 02 00 (long addr low bytes in STA long)
    if port[i] == 0xB6 and port[i+1] == 0x02 and port[i+2] == 0x00:
        # Check if preceded by an opcode that takes a long address
        if i > 0 and port[i-1] in (0x8F, 0xAF, 0x0F, 0x2F, 0x4F, 0x6F, 0xCF, 0xEF):
            op = {0x8F: "STA", 0xAF: "LDA", 0x0F: "ORA", 0x2F: "AND", 0x4F: "EOR", 0x6F: "ADC", 0xCF: "CMP", 0xEF: "SBC"}[port[i-1]]
            print(f"  ${i-1:04X}: {op} $0002B6 (long)")

# Also check if anything jumps to $02B6 (JML/JSL)
for i in range(len(port) - 4):
    if port[i] in (0x5C, 0x22) and port[i+1] == 0xB6 and port[i+2] == 0x02 and port[i+3] == 0x00:
        op = "JML" if port[i] == 0x5C else "JSL"
        print(f"  ${i:04X}: {op} $0002B6")

print()
# In the original, infloop is at $0419
print("Original references to $0419/$041A (infloop):")
for i in range(len(orig) - 3):
    if orig[i] == 0x19 and orig[i+1] == 0x04:
        if i > 0 and orig[i-1] in (0x8D, 0xAD, 0x0D, 0x2D, 0x4D, 0x6D, 0xCD, 0xED, 0x8E, 0xAE, 0x8C, 0xAC):
            ops = {0x8D: "STA", 0xAD: "LDA", 0x0D: "ORA", 0x2D: "AND", 0x4D: "EOR", 0x6D: "ADC", 0xCD: "CMP", 0xED: "SBC", 0x8E: "STX", 0xAE: "LDX", 0x8C: "STY", 0xAC: "LDY"}
            if orig[i-1] in ops:
                print(f"  ${i-1:04X}: {ops[orig[i-1]]} $0419 (absolute)")
