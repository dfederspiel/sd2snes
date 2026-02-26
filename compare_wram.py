#!/usr/bin/env python3
"""
Compare WRAM routines between original (snescom) and port (64tass) menu.bin files.
Searches for byte signatures in the original ROM, then does byte-by-byte comparison.
"""

import sys

ORIG = "/mnt/c/Users/david/code/sd2snes/snes/menu.bin"
PORT = "/mnt/c/Users/david/code/sd2snes/snes-64tass/menu.bin"

# 65816 opcode mnemonics for disassembly context
OPCODES = {
    0x00: ("BRK", 1, "imp"), 0x01: ("ORA", 2, "dpxi"), 0x02: ("COP", 2, "imm8"),
    0x03: ("ORA", 2, "sr"), 0x04: ("TSB", 2, "dp"), 0x05: ("ORA", 2, "dp"),
    0x06: ("ASL", 2, "dp"), 0x07: ("ORA", 2, "dpil"), 0x08: ("PHP", 1, "imp"),
    0x09: ("ORA", 2, "imm"),  # size varies by M flag
    0x0A: ("ASL", 1, "acc"), 0x0B: ("PHD", 1, "imp"), 0x0C: ("TSB", 3, "abs"),
    0x0D: ("ORA", 3, "abs"), 0x0E: ("ASL", 3, "abs"), 0x0F: ("ORA", 4, "long"),
    0x10: ("BPL", 2, "rel8"), 0x11: ("ORA", 2, "dpiy"), 0x12: ("ORA", 2, "dpi"),
    0x13: ("ORA", 2, "sriy"), 0x14: ("TRB", 2, "dp"), 0x15: ("ORA", 2, "dpx"),
    0x16: ("ASL", 2, "dpx"), 0x17: ("ORA", 2, "dpily"), 0x18: ("CLC", 1, "imp"),
    0x19: ("ORA", 3, "absy"), 0x1A: ("INC", 1, "acc"), 0x1B: ("TCS", 1, "imp"),
    0x1C: ("TRB", 3, "abs"), 0x1D: ("ORA", 3, "absx"), 0x1E: ("ASL", 3, "absx"),
    0x1F: ("ORA", 4, "longx"),
    0x20: ("JSR", 3, "abs"), 0x21: ("AND", 2, "dpxi"), 0x22: ("JSL", 4, "long"),
    0x23: ("AND", 2, "sr"), 0x24: ("BIT", 2, "dp"), 0x25: ("AND", 2, "dp"),
    0x26: ("ROL", 2, "dp"), 0x27: ("AND", 2, "dpil"), 0x28: ("PLP", 1, "imp"),
    0x29: ("AND", 2, "imm"),  # varies
    0x2A: ("ROL", 1, "acc"), 0x2B: ("PLD", 1, "imp"), 0x2C: ("BIT", 3, "abs"),
    0x2D: ("AND", 3, "abs"), 0x2E: ("ROL", 3, "abs"), 0x2F: ("AND", 4, "long"),
    0x30: ("BMI", 2, "rel8"), 0x31: ("AND", 2, "dpiy"), 0x32: ("AND", 2, "dpi"),
    0x33: ("AND", 2, "sriy"), 0x34: ("BIT", 2, "dpx"), 0x35: ("AND", 2, "dpx"),
    0x36: ("ROL", 2, "dpx"), 0x37: ("AND", 2, "dpily"), 0x38: ("SEC", 1, "imp"),
    0x39: ("AND", 3, "absy"), 0x3A: ("DEC", 1, "acc"), 0x3B: ("TSC", 1, "imp"),
    0x3C: ("BIT", 3, "absx"), 0x3D: ("AND", 3, "absx"), 0x3E: ("ROL", 3, "absx"),
    0x3F: ("AND", 4, "longx"),
    0x40: ("RTI", 1, "imp"), 0x41: ("EOR", 2, "dpxi"), 0x42: ("WDM", 2, "imm8"),
    0x43: ("EOR", 2, "sr"), 0x44: ("MVP", 3, "blockmv"), 0x45: ("EOR", 2, "dp"),
    0x46: ("LSR", 2, "dp"), 0x47: ("EOR", 2, "dpil"), 0x48: ("PHA", 1, "imp"),
    0x49: ("EOR", 2, "imm"),
    0x4A: ("LSR", 1, "acc"), 0x4B: ("PHK", 1, "imp"), 0x4C: ("JMP", 3, "abs"),
    0x4D: ("EOR", 3, "abs"), 0x4E: ("LSR", 3, "abs"), 0x4F: ("EOR", 4, "long"),
    0x50: ("BVC", 2, "rel8"), 0x51: ("EOR", 2, "dpiy"), 0x52: ("EOR", 2, "dpi"),
    0x53: ("EOR", 2, "sriy"), 0x54: ("MVN", 3, "blockmv"), 0x55: ("EOR", 2, "dpx"),
    0x56: ("LSR", 2, "dpx"), 0x57: ("EOR", 2, "dpily"), 0x58: ("CLI", 1, "imp"),
    0x59: ("EOR", 3, "absy"), 0x5A: ("PHY", 1, "imp"), 0x5B: ("TCD", 1, "imp"),
    0x5C: ("JML", 4, "long"), 0x5D: ("EOR", 3, "absx"), 0x5E: ("LSR", 3, "absx"),
    0x5F: ("EOR", 4, "longx"),
    0x60: ("RTS", 1, "imp"), 0x61: ("ADC", 2, "dpxi"), 0x62: ("PER", 3, "rel16"),
    0x63: ("ADC", 2, "sr"), 0x64: ("STZ", 2, "dp"), 0x65: ("ADC", 2, "dp"),
    0x66: ("ROR", 2, "dp"), 0x67: ("ADC", 2, "dpil"), 0x68: ("PLA", 1, "imp"),
    0x69: ("ADC", 2, "imm"),
    0x6A: ("ROR", 1, "acc"), 0x6B: ("RTL", 1, "imp"), 0x6C: ("JMP", 3, "absi"),
    0x6D: ("ADC", 3, "abs"), 0x6E: ("ROR", 3, "abs"), 0x6F: ("ADC", 4, "long"),
    0x70: ("BVS", 2, "rel8"), 0x71: ("ADC", 2, "dpiy"), 0x72: ("ADC", 2, "dpi"),
    0x73: ("ADC", 2, "sriy"), 0x74: ("STZ", 2, "dpx"), 0x75: ("ADC", 2, "dpx"),
    0x76: ("ROR", 2, "dpx"), 0x77: ("ADC", 2, "dpily"), 0x78: ("SEI", 1, "imp"),
    0x79: ("ADC", 3, "absy"), 0x7A: ("PLY", 1, "imp"), 0x7B: ("TDC", 1, "imp"),
    0x7C: ("JMP", 3, "absxi"), 0x7D: ("ADC", 3, "absx"), 0x7E: ("ROR", 3, "absx"),
    0x7F: ("ADC", 4, "longx"),
    0x80: ("BRA", 2, "rel8"), 0x81: ("STA", 2, "dpxi"), 0x82: ("BRL", 3, "rel16"),
    0x83: ("STA", 2, "sr"), 0x84: ("STY", 2, "dp"), 0x85: ("STA", 2, "dp"),
    0x86: ("STX", 2, "dp"), 0x87: ("STA", 2, "dpil"), 0x88: ("DEY", 1, "imp"),
    0x89: ("BIT", 2, "imm"),
    0x8A: ("TXA", 1, "imp"), 0x8B: ("PHB", 1, "imp"), 0x8C: ("STY", 3, "abs"),
    0x8D: ("STA", 3, "abs"), 0x8E: ("STX", 3, "abs"), 0x8F: ("STA", 4, "long"),
    0x90: ("BCC", 2, "rel8"), 0x91: ("STA", 2, "dpiy"), 0x92: ("STA", 2, "dpi"),
    0x93: ("STA", 2, "sriy"), 0x94: ("STY", 2, "dpx"), 0x95: ("STA", 2, "dpx"),
    0x96: ("STX", 2, "dpx"), 0x97: ("STA", 2, "dpily"), 0x98: ("TYA", 1, "imp"),
    0x99: ("STA", 3, "absy"), 0x9A: ("TXS", 1, "imp"), 0x9B: ("TXY", 1, "imp"),
    0x9C: ("STZ", 3, "abs"), 0x9D: ("STA", 3, "absx"), 0x9E: ("STZ", 3, "absx"),
    0x9F: ("STA", 4, "longx"),
    0xA0: ("LDY", 2, "imm"),  # varies
    0xA1: ("LDA", 2, "dpxi"), 0xA2: ("LDX", 2, "imm"),  # varies
    0xA3: ("LDA", 2, "sr"), 0xA4: ("LDY", 2, "dp"), 0xA5: ("LDA", 2, "dp"),
    0xA6: ("LDX", 2, "dp"), 0xA7: ("LDA", 2, "dpil"), 0xA8: ("TAY", 1, "imp"),
    0xA9: ("LDA", 2, "imm"),
    0xAA: ("TAX", 1, "imp"), 0xAB: ("PLB", 1, "imp"), 0xAC: ("LDY", 3, "abs"),
    0xAD: ("LDA", 3, "abs"), 0xAE: ("LDX", 3, "abs"), 0xAF: ("LDA", 4, "long"),
    0xB0: ("BCS", 2, "rel8"), 0xB1: ("LDA", 2, "dpiy"), 0xB2: ("LDA", 2, "dpi"),
    0xB3: ("LDA", 2, "sriy"), 0xB4: ("LDY", 2, "dpx"), 0xB5: ("LDA", 2, "dpx"),
    0xB6: ("LDX", 2, "dpx"), 0xB7: ("LDA", 2, "dpily"), 0xB8: ("CLV", 1, "imp"),
    0xB9: ("LDA", 3, "absy"), 0xBA: ("TSX", 1, "imp"), 0xBB: ("TYX", 1, "imp"),
    0xBC: ("LDY", 3, "absx"), 0xBD: ("LDA", 3, "absx"), 0xBE: ("LDX", 3, "absy"),
    0xBF: ("LDA", 4, "longx"),
    0xC0: ("CPY", 2, "imm"),  # varies
    0xC1: ("CMP", 2, "dpxi"), 0xC2: ("REP", 2, "imm8"),
    0xC3: ("CMP", 2, "sr"), 0xC4: ("CPY", 2, "dp"), 0xC5: ("CMP", 2, "dp"),
    0xC6: ("DEC", 2, "dp"), 0xC7: ("CMP", 2, "dpil"), 0xC8: ("INY", 1, "imp"),
    0xC9: ("CMP", 2, "imm"),
    0xCA: ("DEX", 1, "imp"), 0xCB: ("WAI", 1, "imp"), 0xCC: ("CPY", 3, "abs"),
    0xCD: ("CMP", 3, "abs"), 0xCE: ("DEC", 3, "abs"), 0xCF: ("CMP", 4, "long"),
    0xD0: ("BNE", 2, "rel8"), 0xD1: ("CMP", 2, "dpiy"), 0xD2: ("CMP", 2, "dpi"),
    0xD3: ("CMP", 2, "sriy"), 0xD4: ("PEI", 2, "dp"), 0xD5: ("CMP", 2, "dpx"),
    0xD6: ("DEC", 2, "dpx"), 0xD7: ("CMP", 2, "dpily"), 0xD8: ("CLD", 1, "imp"),
    0xD9: ("CMP", 3, "absy"), 0xDA: ("PHX", 1, "imp"), 0xDB: ("STP", 1, "imp"),
    0xDC: ("JML", 3, "absil"), 0xDD: ("CMP", 3, "absx"), 0xDE: ("DEC", 3, "absx"),
    0xDF: ("CMP", 4, "longx"),
    0xE0: ("CPX", 2, "imm"),  # varies
    0xE1: ("SBC", 2, "dpxi"), 0xE2: ("SEP", 2, "imm8"),
    0xE3: ("SBC", 2, "sr"), 0xE4: ("CPX", 2, "dp"), 0xE5: ("SBC", 2, "dp"),
    0xE6: ("INC", 2, "dp"), 0xE7: ("SBC", 2, "dpil"), 0xE8: ("INX", 1, "imp"),
    0xE9: ("SBC", 2, "imm"),
    0xEA: ("NOP", 1, "imp"), 0xEB: ("XBA", 1, "imp"), 0xEC: ("CPX", 3, "abs"),
    0xED: ("SBC", 3, "abs"), 0xEE: ("INC", 3, "abs"), 0xEF: ("SBC", 4, "long"),
    0xF0: ("BEQ", 2, "rel8"), 0xF1: ("SBC", 2, "dpiy"), 0xF2: ("SBC", 2, "dpi"),
    0xF3: ("SBC", 2, "sriy"), 0xF4: ("PEA", 3, "abs"), 0xF5: ("SBC", 2, "dpx"),
    0xF6: ("INC", 2, "dpx"), 0xF7: ("SBC", 2, "dpily"), 0xF8: ("SED", 1, "imp"),
    0xF9: ("SBC", 3, "absy"), 0xFA: ("PLX", 1, "imp"), 0xFB: ("XCE", 1, "imp"),
    0xFC: ("JSR", 3, "absxi"), 0xFD: ("SBC", 3, "absx"), 0xFE: ("INC", 3, "absx"),
    0xFF: ("SBC", 4, "longx"),
}


def find_pattern(data, pattern_bytes):
    """Find all occurrences of pattern in data."""
    results = []
    for i in range(len(data) - len(pattern_bytes) + 1):
        if data[i:i+len(pattern_bytes)] == pattern_bytes:
            results.append(i)
    return results


def disasm_line(data, offset, m_flag=True, x_flag=True):
    """Disassemble one instruction. Returns (mnemonic_str, byte_count).
    m_flag/x_flag: True = 8-bit, False = 16-bit."""
    if offset >= len(data):
        return ("???", 1)

    opcode = data[offset]
    if opcode not in OPCODES:
        return (f".db ${opcode:02X}", 1)

    mnem, base_size, mode = OPCODES[opcode]

    # Adjust size for immediate mode instructions affected by M/X flags
    size = base_size
    if mode == "imm":
        if opcode in (0x09, 0x29, 0x49, 0x69, 0x89, 0xA9, 0xC9, 0xE9):  # A-size
            if not m_flag:
                size = 3
        elif opcode in (0xA0, 0xA2, 0xC0, 0xE0):  # X/Y-size
            if not x_flag:
                size = 3

    if offset + size > len(data):
        return (f".db ${opcode:02X}  ; truncated", 1)

    operand_bytes = data[offset+1:offset+size]

    if size == 1:
        result = mnem
    elif mode == "rel8":
        rel = operand_bytes[0]
        if rel > 127:
            rel -= 256
        target = offset + 2 + rel
        result = f"{mnem} ${target:04X}  ; rel {rel:+d}"
    elif mode == "rel16":
        rel = operand_bytes[0] | (operand_bytes[1] << 8)
        if rel > 32767:
            rel -= 65536
        target = offset + 3 + rel
        result = f"{mnem} ${target:04X}  ; rel {rel:+d}"
    elif mode == "blockmv":
        result = f"{mnem} ${operand_bytes[0]:02X}, ${operand_bytes[1]:02X}"
    elif size == 2:
        result = f"{mnem} #${operand_bytes[0]:02X}" if "imm" in mode else f"{mnem} ${operand_bytes[0]:02X}"
    elif size == 3:
        val = operand_bytes[0] | (operand_bytes[1] << 8)
        if "imm" in mode:
            result = f"{mnem} #${val:04X}"
        else:
            suffix = ""
            if mode == "absx": suffix = ",X"
            elif mode == "absy": suffix = ",Y"
            elif mode == "absi": suffix = " (indirect)"
            elif mode == "absxi": suffix = " (indirect,X)"
            result = f"{mnem} ${val:04X}{suffix}"
    elif size == 4:
        val = operand_bytes[0] | (operand_bytes[1] << 8) | (operand_bytes[2] << 16)
        suffix = ",X" if mode == "longx" else ""
        result = f"{mnem} ${val:06X}{suffix}"
    else:
        result = f"{mnem} ???"

    return (result, size)


def disasm_block(data, offset, length, label="", m_flag=True, x_flag=True):
    """Disassemble a block of code, returning list of (offset, bytes_hex, mnemonic)."""
    lines = []
    pos = 0
    while pos < length:
        mnem, size = disasm_line(data, offset + pos, m_flag, x_flag)
        byte_str = " ".join(f"{data[offset+pos+i]:02X}" for i in range(size))

        # Track M/X flag changes
        opcode = data[offset + pos]
        if opcode == 0xC2:  # REP
            val = data[offset + pos + 1]
            if val & 0x20: m_flag = False
            if val & 0x10: x_flag = False
        elif opcode == 0xE2:  # SEP
            val = data[offset + pos + 1]
            if val & 0x20: m_flag = True
            if val & 0x10: x_flag = True

        lines.append((offset + pos, byte_str, mnem, size))
        pos += size
    return lines


def compare_routines(orig_data, port_data, orig_off, port_off, length, name):
    """Compare two routine blocks byte-by-byte with disassembly."""
    print(f"\n{'='*100}")
    print(f"ROUTINE: {name}")
    print(f"Original offset: ${orig_off:04X}  |  Port offset: ${port_off:04X}  |  Length: {length} bytes (${length:02X})")
    print(f"{'='*100}")

    orig_bytes = orig_data[orig_off:orig_off+length]
    port_bytes = port_data[port_off:port_off+length]

    # Quick check
    if orig_bytes == port_bytes:
        print("  ** IDENTICAL - no differences **")
        hex_dump(orig_bytes, orig_off, "Both")
        return True

    # Count differences
    diffs = sum(1 for a, b in zip(orig_bytes, port_bytes) if a != b)
    print(f"  ** {diffs} byte(s) differ **\n")

    # Disassemble both side by side
    orig_lines = disasm_block(orig_data, orig_off, length)
    port_lines = disasm_block(port_data, port_off, length)

    # Show byte comparison with disassembly
    print(f"  {'ORIG OFF':>8}  {'ORIG BYTES':<20} {'ORIG ASM':<30} | {'PORT OFF':>8}  {'PORT BYTES':<20} {'PORT ASM':<30}  DIFF?")
    print(f"  {'-'*8}  {'-'*20} {'-'*30} | {'-'*8}  {'-'*20} {'-'*30}  {'-'*5}")

    # Build maps: offset -> line
    orig_map = {}
    for off, bstr, mnem, sz in orig_lines:
        orig_map[off - orig_off] = (bstr, mnem, sz)
    port_map = {}
    for off, bstr, mnem, sz in port_lines:
        port_map[off - port_off] = (bstr, mnem, sz)

    # Walk through instruction by instruction
    # If instructions align, show side by side. If not, flag structural difference.
    oi = 0
    pi = 0
    orig_instrs = [(off - orig_off, bstr, mnem, sz) for off, bstr, mnem, sz in orig_lines]
    port_instrs = [(off - port_off, bstr, mnem, sz) for off, bstr, mnem, sz in port_lines]

    oidx = 0
    pidx = 0

    while oidx < len(orig_instrs) or pidx < len(port_instrs):
        if oidx < len(orig_instrs):
            orel, obstr, omnem, osz = orig_instrs[oidx]
        else:
            orel, obstr, omnem, osz = (-1, "", "", 0)

        if pidx < len(port_instrs):
            prel, pbstr, pmnem, psz = port_instrs[pidx]
        else:
            prel, pbstr, pmnem, psz = (-1, "", "", 0)

        # Check if bytes differ at this position
        if orel >= 0 and prel >= 0 and orel == prel:
            # Aligned - compare
            ob = orig_bytes[orel:orel+max(osz, psz)]
            pb = port_bytes[prel:prel+max(osz, psz)]
            diff_marker = ""
            if osz != psz:
                diff_marker = " <<<< SIZE DIFF!"
            elif ob[:osz] != pb[:psz]:
                diff_marker = " <<<< DIFFERS!"

            print(f"  ${orig_off+orel:04X}     {obstr:<20} {omnem:<30} | ${port_off+prel:04X}     {pbstr:<20} {pmnem:<30}  {diff_marker}")
            oidx += 1
            pidx += 1
        elif orel >= 0 and prel >= 0:
            # Misaligned - structural difference
            if orel < prel:
                print(f"  ${orig_off+orel:04X}     {obstr:<20} {omnem:<30} | {'':>8}  {'':20} {'':30}  <<<< ONLY IN ORIG")
                oidx += 1
            else:
                print(f"  {'':>8}  {'':20} {'':30} | ${port_off+prel:04X}     {pbstr:<20} {pmnem:<30}  <<<< ONLY IN PORT")
                pidx += 1
        elif orel >= 0:
            print(f"  ${orig_off+orel:04X}     {obstr:<20} {omnem:<30} | {'':>8}  {'':20} {'':30}  <<<< ONLY IN ORIG")
            oidx += 1
        else:
            print(f"  {'':>8}  {'':20} {'':30} | ${port_off+prel:04X}     {pbstr:<20} {pmnem:<30}  <<<< ONLY IN PORT")
            pidx += 1

    # Raw hex dump for reference
    print(f"\n  Raw hex comparison:")
    for i in range(0, length, 16):
        chunk = min(16, length - i)
        orig_hex = " ".join(f"{orig_bytes[i+j]:02X}" for j in range(chunk))
        port_hex = " ".join(f"{port_bytes[i+j]:02X}" for j in range(chunk))
        markers = ""
        for j in range(chunk):
            if orig_bytes[i+j] != port_bytes[i+j]:
                markers += f" [+{i+j:02X}]"
        print(f"    +${i:02X}: ORIG: {orig_hex}")
        print(f"    +${i:02X}: PORT: {port_hex}{' <<<' + markers if markers else ''}")

    return False


def hex_dump(data, base_offset, label):
    """Print hex dump of data."""
    for i in range(0, len(data), 16):
        chunk = min(16, len(data) - i)
        hex_str = " ".join(f"{data[i+j]:02X}" for j in range(chunk))
        print(f"    ${base_offset+i:04X}: {hex_str}")


def main():
    with open(ORIG, "rb") as f:
        orig = bytearray(f.read())
    with open(PORT, "rb") as f:
        port = bytearray(f.read())

    print(f"Original size: {len(orig)} bytes")
    print(f"Port size:     {len(port)} bytes")

    # Define the routines we're looking for
    routines = [
        {
            "name": "wram_routine_src (FPGA reconfig, -> $7EF000)",
            "signature": bytes([0x08, 0xE2, 0x20, 0xC2, 0x10, 0xA9, 0x0B, 0x8F, 0x00, 0x2A, 0x00]),
            "port_offset": 0x08B6,
            "port_length": 28,
        },
        {
            "name": "store_blockram_routine_src (-> $7EF080)",
            "signature": bytes([0x08, 0xE2, 0x20, 0xC2, 0x10, 0xA9, 0x80]),
            "port_offset": 0x08D3,
            "port_length": 35,
        },
        {
            "name": "fadeloop (-> $7EF100)",
            "signature": bytes([0xE2, 0x30, 0x4B, 0xAB, 0x9C, 0x00, 0x42, 0x78]),
            "port_offset": 0x08F6,
            "port_length": 133,
        },
        {
            "name": "wram_wait_mcu_src (-> $7EF200)",
            "signature": bytes([0xAF, 0x02, 0x2A, 0x00, 0xC9, 0x55]),
            "port_offset": 0x097B,
            "port_length": 11,
        },
    ]

    all_identical = True

    for r in routines:
        # Find in original
        matches = find_pattern(orig, r["signature"])

        if not matches:
            print(f"\n{'='*100}")
            print(f"ROUTINE: {r['name']}")
            print(f"  !! SIGNATURE NOT FOUND IN ORIGINAL !!")
            print(f"  Searching with shorter signature...")
            # Try shorter signature
            for sig_len in range(len(r["signature"]) - 1, 3, -1):
                matches = find_pattern(orig, r["signature"][:sig_len])
                if matches:
                    print(f"  Found {len(matches)} match(es) with {sig_len}-byte prefix: {[f'${m:04X}' for m in matches]}")
                    break
            if not matches:
                print(f"  !! Could not find routine at all !!")
                all_identical = False
                continue

        if len(matches) > 1:
            print(f"\n  WARNING: Multiple matches for {r['name']}: {[f'${m:04X}' for m in matches]}")
            print(f"  Using first match.")

        orig_off = matches[0]

        # Determine actual length - look for RTL (0x6B) to find end
        # Use port length as our guide, but also look a bit further
        search_len = r["port_length"] + 16
        found_rtl = None
        for i in range(r["port_length"] - 1, search_len):
            if orig_off + i < len(orig) and orig[orig_off + i] == 0x6B:
                found_rtl = i + 1  # include the RTL
                break

        orig_length = found_rtl if found_rtl else r["port_length"]

        # Use the larger of the two lengths for comparison
        compare_len = max(orig_length, r["port_length"])

        print(f"\n  Original routine length (to RTL): {orig_length} bytes")
        print(f"  Port routine length: {r['port_length']} bytes")

        if orig_length != r["port_length"]:
            print(f"  !! LENGTH MISMATCH: orig={orig_length} port={r['port_length']} !!")
            # Show both at their respective lengths
            print(f"\n  --- Original ({orig_length} bytes) ---")
            orig_lines = disasm_block(orig, orig_off, orig_length)
            for off, bstr, mnem, sz in orig_lines:
                print(f"    ${off:04X}  {bstr:<20} {mnem}")

            print(f"\n  --- Port ({r['port_length']} bytes) ---")
            port_lines = disasm_block(port, r["port_offset"], r["port_length"])
            for off, bstr, mnem, sz in port_lines:
                print(f"    ${off:04X}  {bstr:<20} {mnem}")

            all_identical = False
        else:
            identical = compare_routines(orig, port, orig_off, r["port_offset"], compare_len, r["name"])
            if not identical:
                all_identical = False

    # Also check the DMA copy sizes in store_wram_routines
    print(f"\n{'='*100}")
    print("STORE_WRAM_ROUTINES DMA COPY SIZE CHECK")
    print(f"{'='*100}")

    # Search for DMA7 transfers to $7EF000, $7EF080, $7EF100, $7EF200
    # DMA7 writes: $4370=mode, $4371=dest, $4372-4374=src, $4375-4376=size
    # The size register is at $4375 (low) and $4376 (high)
    # Look for writes to $4375/$4376 near WRAM destination setup

    # Search for $F000 in both (destination $7EF000 low bytes written to $2181)
    targets = [
        ("$7EF000 (wram_routine)", 0xF000, 28),
        ("$7EF080 (store_blockram)", 0xF080, 35),
        ("$7EF100 (fadeloop)", 0xF100, 133),
        ("$7EF200 (wram_wait_mcu)", 0xF200, 11),
    ]

    print("\n  Checking for DMA7 transfer size values in both ROMs...")
    print("  (Looking for the byte patterns that set transfer sizes)")

    # Actually, let's find store_wram_routines itself
    # It uses DMA7 macro which writes to $43x0-$43x6
    # Let's search for writes to $4375 (DMA7 size low byte)
    # Pattern: A9 xx 8D 75 43 (LDA #imm8, STA $4375)
    # Or: A2 xxxx 8E 75 43 (LDX #imm16, STX $4375)

    for label, rom_name, data in [("ORIGINAL", "snescom", orig), ("PORT", "64tass", port)]:
        print(f"\n  --- {label} ({rom_name}) ---")
        # Find all DMA channel 7 size writes: STA $4375 = 8D 75 43 or STX $4375 = 8E 75 43
        for i in range(len(data) - 3):
            if data[i] == 0x8D and data[i+1] == 0x75 and data[i+2] == 0x43:
                # STA $4375 - what was loaded into A?
                # Look back for LDA
                context_start = max(0, i - 16)
                context = " ".join(f"{data[j]:02X}" for j in range(context_start, i + 3))
                print(f"    STA $4375 at ${i:04X}, context: ...{context}")
            if data[i] == 0x8E and data[i+1] == 0x75 and data[i+2] == 0x43:
                context_start = max(0, i - 16)
                context = " ".join(f"{data[j]:02X}" for j in range(context_start, i + 3))
                print(f"    STX $4375 at ${i:04X}, context: ...{context}")

    print(f"\n{'='*100}")
    if all_identical:
        print("RESULT: All WRAM routines are IDENTICAL between original and port.")
    else:
        print("RESULT: Differences found! See details above.")
    print(f"{'='*100}")


if __name__ == "__main__":
    main()
