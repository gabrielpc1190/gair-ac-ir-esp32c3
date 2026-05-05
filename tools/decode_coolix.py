#!/usr/bin/env python3
"""Decode raw IR timings to 24-bit Coolix hex codes.

Reads a JSON file with capture slots (output of extract_captures.py) and decodes
each slot's first frame to its 24-bit Coolix hex code.

Usage:
    python decode_coolix.py _cool_25_fan_high_captures.json

Each capture should be 200 timings forming a Coolix double-frame:
    [hdr_mark][hdr_space][24 bits][24 bits inverted][gap][hdr][24 bits][24 bits inv][end]

Output:
    slot 0: 0xB23FC0  [Cool 25 fan HIGH]  invOK=True
    slot 1: 0xB23FC0  [Cool 25 fan HIGH]  invOK=True
    slot 2: 0xB2BFC0  [Cool 25 fan AUTO]  invOK=True   ← FAN cycled

Use this to verify which slot has your desired button code, then embed those
timings into firmware/gair-ir.yaml.
"""

import argparse
import json
import sys

# Known GAir/Coolix codes (verified from physical remote captures).
# Add yours here as you decode them.
KNOWN_CODES = {
    # Power
    0xB27BE0: "POWER OFF",
    # Toggles
    0xB5F5A5: "LCD toggle",
    0xB26BE0: "Swing toggle",
    0xB5F5A2: "Turbo toggle",
    # Cool 24°C
    0xB23F40: "Cool 24 fan HIGH",
    0xB25F40: "Cool 24 fan MID",
    0xB29F40: "Cool 24 fan LOW",
    0xB2BF40: "Cool 24 fan AUTO",
    # Cool 25°C
    0xB23FC0: "Cool 25 fan HIGH",
    0xB25FC0: "Cool 25 fan MID",
    0xB29FC0: "Cool 25 fan LOW",
    0xB2BFC0: "Cool 25 fan AUTO",
    # Cool 26°C
    0xB23FD0: "Cool 26 fan HIGH",
    0xB25FD0: "Cool 26 fan MID",
    0xB29FD0: "Cool 26 fan LOW",
    0xB2BFD0: "Cool 26 fan AUTO",
    # Fan-only mode
    0xB23FE4: "Fan Only HIGH",
    0xB25FE4: "Fan Only MID",
    0xB29FE4: "Fan Only LOW",
    0xB2BFE4: "Fan Only AUTO",
    # Other modes (less tested)
    0xB21F94: "DRY mode",
    0xB21F98: "AUTO mode",
}


def decode_coolix(timings: list[int]) -> tuple[int | None, bool, list[int]]:
    """Decode raw IR timings to 24-bit Coolix hex.

    Returns:
        (hex_code, inversion_valid, byte_sequence)
        hex_code is None if decoding fails (insufficient timings).
        inversion_valid is True if the [B0,~B0,B1,~B1,B2,~B2] structure validates.
    """
    if len(timings) < 100:
        return None, False, []

    # Skip header pair (first 2 entries: long mark + long space)
    # Then 48 bit-pairs (mark + space each) = 96 entries
    bits = ""
    for i in range(2, 2 + 96, 2):
        if i + 1 >= len(timings):
            break
        space = abs(timings[i + 1])
        # Coolix: bit-1 has space ~1640µs, bit-0 has space ~555µs.
        # Threshold at 1000µs cleanly separates them.
        bits += "1" if space > 1000 else "0"

    if len(bits) < 48:
        return None, False, []

    # Coolix transmits 6 bytes: [B0, ~B0, B1, ~B1, B2, ~B2] MSB-first per byte.
    # The "real" 24-bit code uses bytes 0, 2, 4 (the data bytes; even indices).
    bytes_seq = [int(bits[i * 8 : (i + 1) * 8], 2) for i in range(6)]
    # Validate: each pair should sum to 0xFF (one is the inverse of the other).
    inv_valid = all((bytes_seq[2 * i] ^ bytes_seq[2 * i + 1]) == 0xFF for i in range(3))
    code = (bytes_seq[0] << 16) | (bytes_seq[2] << 8) | bytes_seq[4]
    return code, inv_valid, bytes_seq


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("captures_json", help="Path to a captures JSON file (e.g. _cool_25_fan_high_captures.json)")
    parser.add_argument("--show-bytes", action="store_true", help="Show the full 6-byte sequence")
    args = parser.parse_args()

    with open(args.captures_json, "r") as f:
        captures = json.load(f)

    # Captures may be in two formats:
    # 1. {"0": [timings], "1": [timings], ...}  — raw extract_captures.py output
    # 2. {"buttons": {label: {"timings": [...], ...}, ...}}  — annotated master file
    if "buttons" in captures:
        items = [(label, btn["timings"]) for label, btn in captures["buttons"].items()]
        kind = "master"
    else:
        items = [(slot, timings) for slot, timings in sorted(captures.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999)]
        kind = "raw slots"

    print(f"Decoding {len(items)} captures ({kind}):\n")

    for label_or_slot, timings in items:
        code, inv_valid, bytes_seq = decode_coolix(timings)
        if code is None:
            print(f"  {label_or_slot}: <insufficient timings: {len(timings)}>")
            continue
        known = KNOWN_CODES.get(code, "?")
        valid_marker = "✓" if inv_valid else "✗"
        line = f"  {label_or_slot}: 0x{code:06X}  [{known}]  invOK={inv_valid} {valid_marker}"
        if args.show_bytes:
            line += f"  bytes={bytes_seq}"
        print(line)

    # Summary
    if kind == "raw slots":
        codes_seen = set()
        for _, timings in items:
            code, _, _ = decode_coolix(timings)
            if code is not None:
                codes_seen.add(code)
        print(f"\nDistinct codes seen: {len(codes_seen)}")
        for code in sorted(codes_seen):
            print(f"  0x{code:06X}  [{KNOWN_CODES.get(code, '?')}]")


if __name__ == "__main__":
    main()
