#!/usr/bin/env python3
"""Targeted comparison of specific routines."""

with open("/mnt/c/Users/david/code/sd2snes/snes/menu.bin", "rb") as f:
    orig = bytearray(f.read())
with open("/mnt/c/Users/david/code/sd2snes/snes-64tass/menu.bin", "rb") as f:
    port = bytearray(f.read())

def hexdump(data, offset, length, label):
    print(f"  {label} at ${offset:04X}:")
    for i in range(0, length, 16):
        chunk = min(16, length - i)
        h = " ".join(f"{data[offset+i+j]:02X}" for j in range(chunk))
        print(f"    +${i:02X}: {h}")

# ==========================================================================
# 1. wram_wait_mcu_src - tight loop version
# ==========================================================================
print("=" * 80)
print("1. wram_wait_mcu_src")
print("=" * 80)

# Find in original: AF 02 2A 00 C9 55 D0 F8 6B
pattern = bytes([0xAF, 0x02, 0x2A, 0x00, 0xC9, 0x55, 0xD0, 0xF8, 0x6B])
orig_matches = []
for i in range(len(orig) - len(pattern) + 1):
    if orig[i:i+len(pattern)] == pattern:
        orig_matches.append(i)

print(f"  Original tight loop matches: {['${:04X}'.format(m) for m in orig_matches]}")
print(f"  Original routine length: {len(pattern)} bytes")

port_off = 0x097B
port_len = 11  # claimed length
print(f"\n  Port at ${port_off:04X}, claimed {port_len} bytes:")
hexdump(port, port_off, port_len, "PORT")

# The port's wram_wait_mcu_src should be 9 bytes (the tight loop), not 11
# Let's check: port[097B..0983] should be AF 02 2A 00 C9 55 D0 F8 6B
port_routine = port[port_off:port_off+9]
print(f"\n  Port first 9 bytes: {' '.join(f'{b:02X}' for b in port_routine)}")
print(f"  Original pattern:   {' '.join(f'{b:02X}' for b in pattern)}")
print(f"  Match: {port_routine == bytearray(pattern)}")

if orig_matches:
    orig_off = orig_matches[0]
    orig_routine = orig[orig_off:orig_off+9]
    print(f"\n  Original at ${orig_off:04X}: {' '.join(f'{b:02X}' for b in orig_routine)}")
    print(f"  IDENTICAL: {orig_routine == port_routine}")

print(f"\n  Bytes 9-10 past routine in port: {' '.join(f'{port[port_off+i]:02X}' for i in range(9, port_len))}")
print(f"  (These are start of next routine/data, not part of wram_wait_mcu_src)")

# ==========================================================================
# 2. wram_routine_src - FPGA reconfig
# ==========================================================================
print("\n" + "=" * 80)
print("2. wram_routine_src (FPGA reconfig)")
print("=" * 80)

# Port: 28 bytes at $08B6
# Original: found at $09D3, 29 bytes (includes RTL)
# The port is MISSING the RTL!

port_off = 0x08B6
port_len = 28

# Search original for the same prefix
sig = bytes([0x08, 0xE2, 0x20, 0xC2, 0x10, 0xA9, 0x0B, 0x8F, 0x00, 0x2A, 0x00])
orig_matches = []
for i in range(len(orig) - len(sig) + 1):
    if orig[i:i+len(sig)] == sig:
        orig_matches.append(i)

print(f"  Original matches: {['${:04X}'.format(m) for m in orig_matches]}")

if orig_matches:
    orig_off = orig_matches[0]

    # Find RTL
    for j in range(port_len + 4):
        if orig[orig_off + j] == 0x6B:
            orig_len = j + 1
            break

    print(f"  Original at ${orig_off:04X}, length {orig_len} bytes (to RTL)")
    print(f"  Port at ${port_off:04X}, length {port_len} bytes")
    print(f"  SIZE DIFFERENCE: orig={orig_len} port={port_len}")

    hexdump(orig, orig_off, orig_len, "ORIG")
    hexdump(port, port_off, port_len, "PORT")

    # Check if port ends with RTL
    last_byte = port[port_off + port_len - 1]
    print(f"\n  Port last byte: ${last_byte:02X} ({'RTL' if last_byte == 0x6B else 'NOT RTL - ' + hex(last_byte)})")

    # Check what's at port_off + 28 (byte after claimed end)
    after = port[port_off + port_len]
    print(f"  Port byte at +{port_len}: ${after:02X} ({'RTL' if after == 0x6B else hex(after)})")

    # Byte-by-byte comparison
    print(f"\n  Byte-by-byte comparison (up to {max(orig_len, port_len)} bytes):")
    max_len = max(orig_len, port_len + 1)  # +1 to check for missing RTL
    for i in range(max_len):
        ob = orig[orig_off + i] if orig_off + i < len(orig) else None
        pb = port[port_off + i] if port_off + i < len(port) and i < port_len + 1 else None
        marker = ""
        if ob is not None and pb is not None and ob != pb:
            marker = " <<<< DIFFERS"
        elif ob is None:
            marker = " <<<< only in port"
        elif pb is None:
            marker = " <<<< only in orig"
        ob_str = f"${ob:02X}" if ob is not None else "---"
        pb_str = f"${pb:02X}" if pb is not None else "---"
        print(f"    +${i:02X}: orig={ob_str}  port={pb_str}{marker}")

# ==========================================================================
# 3. store_blockram_routine_src
# ==========================================================================
print("\n" + "=" * 80)
print("3. store_blockram_routine_src")
print("=" * 80)

port_off = 0x08D3
port_len = 35

# The key difference found was STA $0419 (absolute) vs STA $0002B6 (long)
# Let's find the CORRECT original match (not the one at $09B2 which might be wrong)

# The original's store_blockram_routine should be near the other WRAM routines
# Let's search for the signature: 08 E2 20 C2 10 A9 80
sig = bytes([0x08, 0xE2, 0x20, 0xC2, 0x10, 0xA9, 0x80])
orig_matches = []
for i in range(len(orig) - len(sig) + 1):
    if orig[i:i+len(sig)] == sig:
        orig_matches.append(i)

print(f"  Original signature matches: {['${:04X}'.format(m) for m in orig_matches]}")

for m in orig_matches:
    # Show first 40 bytes of each match
    end = min(len(orig), m + 40)
    h = " ".join(f"{orig[j]:02X}" for j in range(m, end))
    print(f"    ${m:04X}: {h}")

    # Check if it contains MVN
    for j in range(40):
        if m + j < len(orig) and orig[m + j] == 0x54:  # MVN
            mvn_off = m + j
            print(f"      MVN at +${j:02X}: 54 {orig[mvn_off+1]:02X} {orig[mvn_off+2]:02X}")
            # WDC encoding: 54 dst src
            # snescom writes: mvn dst, src -> encodes 54 dst src
            # 64tass writes: mvn src, dst -> encodes 54 dst src
            # So encoded bytes should be same either way if the source was written correctly
            print(f"        Encoded as: MVN dst=${orig[mvn_off+1]:02X} src=${orig[mvn_off+2]:02X}")

# Now compare the two matches with the port
# The first match ($09B2) has STA $0419 (3-byte abs: 8D 19 04)
# The second match ($0AC3) might be different
# Port has STA $0002B6 (4-byte long: 8F B6 02 00)

print(f"\n  PORT routine:")
hexdump(port, port_off, port_len, "PORT")

print(f"\n  KEY DIFFERENCE: Addressing modes")
print(f"  Original at $09B9: 8D 19 04     -> STA $0419 (3-byte absolute)")
print(f"  Port at     $08DA: 8F B6 02 00  -> STA $0002B6 (4-byte long)")
print(f"  These are DIFFERENT ADDRESSES! $0419 vs $02B6")
print(f"  This means the port is writing to a completely different memory location!")

# What are these addresses?
print(f"\n  $0419 in original: likely a WRAM variable (direct page or low RAM)")
print(f"  $02B6 in port: likely a WRAM variable (different address allocation)")
print(f"  This difference is expected if variables are at different addresses,")
print(f"  BUT the addressing mode change (abs -> long) adds 1 byte per STA,")
print(f"  which shifts all subsequent bytes and changes the routine length.")

# Check if both routines are the same length
for m in orig_matches:
    for j in range(50):
        if m + j < len(orig) and orig[m + j] == 0x6B:
            print(f"  Original match at ${m:04X}: RTL at +${j:02X}, total {j+1} bytes")
            break

# ==========================================================================
# 4. fadeloop - the big one
# ==========================================================================
print("\n" + "=" * 80)
print("4. fadeloop (133 bytes)")
print("=" * 80)

port_off = 0x08F6
port_len = 133

# Original at $08DD, 133 bytes
orig_off = 0x08DD

print(f"  Both are {port_len} bytes - same length")
print()

# The key difference: at offset +$0B
# Original: AE 1C 04 -> LDX $041C (3-byte absolute)
# Port:     A6 31    -> LDX $31   (2-byte direct page)
print("  CRITICAL DIFFERENCE at +$0B:")
print(f"  Original: AE 1C 04 -> LDX $041C (absolute addressing, 3 bytes)")
print(f"  Port:     A6 31    -> LDX $31   (direct page addressing, 2 bytes)")
print(f"  This is a 1-byte size difference that shifts ALL subsequent code!")
print()

# But both are 133 bytes total... how?
# The port must have an extra byte somewhere else to compensate
# Let's find exactly where the streams diverge and re-sync

print("  Searching for where bytes diverge and re-sync...")
diverge_points = []
in_diff = False
for i in range(port_len):
    ob = orig[orig_off + i]
    pb = port[port_off + i]
    if ob != pb and not in_diff:
        diverge_points.append(("START", i))
        in_diff = True
    elif ob == pb and in_diff:
        diverge_points.append(("END", i))
        in_diff = False

if in_diff:
    diverge_points.append(("END", port_len))

print(f"  Divergence regions:")
for dtype, pos in diverge_points:
    if dtype == "START":
        print(f"    Bytes differ starting at +${pos:02X}")
    else:
        print(f"    Bytes re-sync at +${pos:02X}")

# The 1-byte shift means everything after the LDX instruction is off by 1
# But the total length is the same (133 bytes)
# This means the routine content is effectively the same, just shifted
# Let's verify by comparing orig[0B:0B+3] with port[0B:0B+2] then checking alignment

print(f"\n  Detailed instruction-level comparison around the divergence:")
print(f"  Original +$08..+$0F: {' '.join(f'{orig[orig_off+i]:02X}' for i in range(0x08, 0x10))}")
print(f"  Port     +$08..+$0F: {' '.join(f'{port[port_off+i]:02X}' for i in range(0x08, 0x10))}")

# Check if the shift is exactly 1 byte throughout
print(f"\n  Checking if port[+$0D:] == orig[+$0E:] (1-byte shift):")
match_count = 0
mismatch_at = []
for i in range(0x0E, port_len):
    if i - 1 < port_len and orig[orig_off + i] == port[port_off + i - 1]:
        match_count += 1
    else:
        mismatch_at.append(i)

print(f"    Matched {match_count} bytes with 1-byte offset")
if mismatch_at:
    print(f"    Mismatches at original offsets: {['${:02X}'.format(m) for m in mismatch_at[:20]]}")
    for m in mismatch_at[:10]:
        ob = orig[orig_off + m] if orig_off + m < len(orig) else 0
        pb = port[port_off + m - 1] if port_off + m - 1 < len(port) else 0
        print(f"      +${m:02X}: orig=${ob:02X} port(shifted)=${pb:02X}")

# The fadeloop has branch instructions - their relative offsets should be the same
# since the routine lives in WRAM at a fixed address. But if the LDX is 1 byte shorter,
# branches WITHIN the routine need to be adjusted.
# Let's check all branch instructions
print(f"\n  Branch instructions in fadeloop:")
print(f"  {'':>5} {'ORIG':^20} {'PORT':^20}")
# Walk original
i = 0
while i < port_len:
    ob = orig[orig_off + i]
    if ob in (0x10, 0x30, 0x50, 0x70, 0x80, 0x90, 0xB0, 0xD0, 0xF0):
        orel = orig[orig_off + i + 1]
        if orel > 127: orel -= 256
        otarget = i + 2 + orel
        # Find same instruction in port
        # Due to 1-byte shift, it should be at i-1 in port (after offset +$0B)
        if i >= 0x0E:
            pi = i - 1
        else:
            pi = i
        pb = port[port_off + pi] if pi < port_len else 0
        if pb == ob:
            prel = port[port_off + pi + 1]
            if prel > 127: prel -= 256
            ptarget = pi + 2 + prel
            branch_name = {0x10:"BPL",0x30:"BMI",0x50:"BVC",0x70:"BVS",0x80:"BRA",0x90:"BCC",0xB0:"BCS",0xD0:"BNE",0xF0:"BEQ"}[ob]
            diff_marker = " <<<< BRANCH TARGET DIFFERS" if orel != prel else ""
            print(f"  +${i:02X}: {branch_name} rel={orel:+d} -> +${otarget:02X} | +${pi:02X}: {branch_name} rel={prel:+d} -> +${ptarget:02X}{diff_marker}")
        i += 2
    else:
        i += 1

# ==========================================================================
# 5. DMA copy sizes (store_wram_routines)
# ==========================================================================
print("\n" + "=" * 80)
print("5. DMA copy sizes for WRAM routine transfers")
print("=" * 80)

# In store_wram_routines, the code does multiple DMA7 transfers
# Each one sets $4375/$4376 = transfer size
# We need to find the sizes used for the 4 WRAM targets:
# $7EF000, $7EF080, $7EF100, $7EF200

# Look for patterns that set $2181 (WRAM address low) to F000, F080, F100, F200
# Pattern: LDX #xxxx / STX $2181 = A2 xx xx 8E 81 21

for label, data in [("ORIGINAL", orig), ("PORT", port)]:
    print(f"\n  --- {label} ---")
    for i in range(len(data) - 6):
        if data[i] == 0xA2 and data[i+3] == 0x8E and data[i+4] == 0x81 and data[i+5] == 0x21:
            addr_lo = data[i+1]
            addr_hi = data[i+2]
            addr = addr_lo | (addr_hi << 8)
            if addr in (0xF000, 0xF080, 0xF100, 0xF200):
                # Now find the size - look for STX $4375 nearby (within 30 bytes)
                for j in range(i+6, min(i+40, len(data)-3)):
                    if data[j] == 0x8E and data[j+1] == 0x75 and data[j+2] == 0x43:
                        # Found STX $4375 - what was loaded?
                        # Look back for LDX
                        for k in range(j-1, max(j-6, 0), -1):
                            if data[k] == 0xA2:
                                size_lo = data[k+1]
                                size_hi = data[k+2]
                                size = size_lo | (size_hi << 8)
                                target_name = {0xF000: "wram_routine", 0xF080: "store_blockram", 0xF100: "fadeloop", 0xF200: "wram_wait_mcu"}[addr]
                                print(f"    WRAM ${addr:04X} ({target_name}): DMA size = ${size:04X} ({size} bytes)")
                                break
                        break

# ==========================================================================
# 6. Summary of all issues found
# ==========================================================================
print("\n" + "=" * 80)
print("SUMMARY OF ALL DIFFERENCES")
print("=" * 80)

print("""
1. wram_routine_src (FPGA reconfig, -> $7EF000):
   - Original: 29 bytes (includes RTL at end)
   - Port: 28 bytes (MISSING RTL!)
   - The DMA copy size must include the RTL byte or execution will run off
     into garbage memory after the routine.

2. store_blockram_routine_src (-> $7EF080):
   - ADDRESSING MODE DIFFERENCE:
     Original: STA $0419 / STA $041A (absolute, 3 bytes each)
     Port:     STA $0002B6 / STA $0002B7 (long, 4 bytes each)
   - Different variable addresses ($0419/$041A vs $02B6/$02B7)
   - Long addressing adds 2 extra bytes total, but both routines are 35 bytes
   - MVN operand bytes: check encoding carefully

3. fadeloop (-> $7EF100):
   - ADDRESSING MODE DIFFERENCE at +$0B:
     Original: LDX $041C (absolute, 3 bytes: AE 1C 04)
     Port:     LDX $31   (direct page, 2 bytes: A6 31)
   - This 1-byte shift propagates through ALL remaining instructions
   - Despite the shift, both are 133 bytes total
   - Branch relative offsets should be the same (relative addressing is
     position-independent), but targets shift by 1 byte in WRAM

4. wram_wait_mcu_src (-> $7EF200):
   - Both have identical 9-byte tight loop: AF 02 2A 00 C9 55 D0 F8 6B
   - Port claims 11 bytes but only 9 are the routine (bytes 9-10 are next data)
""")

if __name__ == "__main__":
    pass
