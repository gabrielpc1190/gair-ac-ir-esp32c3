# Coolix Protocol — GAir Variant

GAir uses a Coolix-family IR protocol with specific bit layouts. This is mostly compatible with `IRremoteESP8266`'s built-in Coolix decoder but has a few quirks.

## Frame structure

Each transmission is a **double-frame** to ensure reliability:

```
[hdr_mark][hdr_space][24 bits][24 bits inverted][gap][hdr_mark][hdr_space][24 bits][24 bits inverted][trailing_mark][long_gap]
```

In raw timing notation (microseconds; positive = mark, negative = space):

```
4413, -4380,                                ← header
539, -1639, 537, -557, 535, -1646, ...      ← 24 bits + 24 inverted = 48 bit-pairs = 96 timings
... 535, -25000,                            ← end of first frame (long gap)
4413, -4380,                                ← second frame header
539, -1639, 537, -557, ...                  ← repeat: 24 bits + 24 inverted
... 535, -25000                             ← end
```

Total: ~200 timings (1 mark + 1 space) × 100 = ~200 entries.

## Bit timing

| Element | Mark | Space |
|---|---|---|
| Header | ~4400µs | ~4400µs |
| Bit "1" | ~535µs | ~1640µs |
| Bit "0" | ~535µs | ~555µs |
| Trailer | ~535µs | (gap to next frame ~25ms) |

Carrier: **38028 Hz** with 50% duty cycle (matches IRremoteESP8266 Coolix default; pronto unit `0x6D` = 109 maps to this).

## Bit transmission order

The 24-bit code is transmitted **MSB-first** in the order:

```
[B0 high → B0 low][~B0 high → ~B0 low][B1 high → B1 low][~B1 high → ~B1 low][B2 high → B2 low][~B2 high → ~B2 low]
```

Where `~X` is the bitwise NOT of byte X. This per-byte inversion is the redundancy mechanism — the receiver verifies each byte against its inverse.

So a captured 48-bit string is structured as:
```
[B0=8 bits][~B0=8 bits][B1=8 bits][~B1=8 bits][B2=8 bits][~B2=8 bits]
```

The "real" 24-bit code is `(B0 << 16) | (B1 << 8) | B2` — bytes 0, 2, 4 from the bit stream.

## Decoded hex codes (verified for our GAir model)

### Power & Toggles

| Function | Hex |
|---|---|
| POWER OFF | `0xB27BE0` |
| LCD toggle (display on/off) | `0xB5F5A5` |
| SWING toggle (vertical) | `0xB26BE0` |

### Cool mode + Fan speed states (all turn AC ON)

| Temp | Fan AUTO | Fan LOW | Fan MID | Fan HIGH |
|---|---|---|---|---|
| 24°C | `0xB2BF40` | `0xB29F40` | `0xB25F40` | `0xB23F40` |
| 25°C | `0xB2BFC0` | `0xB29FC0` | `0xB25FC0` | `0xB23FC0` |
| 26°C | `0xB2BFD0` | `0xB29FD0` | `0xB25FD0` | `0xB23FD0` |

### Fan-Only mode (no cooling, just ventilation)

| Speed | Hex |
|---|---|
| Fan Only LOW | `0xB29FE4` |
| Fan Only MID | `0xB25FE4` (untested but pattern-consistent) |
| Fan Only HIGH | `0xB23FE4` |
| Fan Only AUTO | `0xB2BFE4` (untested) |

## Bit-level field decoding

Looking at the hex pattern `0xB2 [byte1] [byte2]`:

- **B0 = 0xB2 always** (Coolix family identifier)
- **B1** encodes mode + fan speed:
  - Bits 7-4 (high nibble): fan speed
    - `0x2` = AUTO (rare alternative)
    - `0xB` = AUTO (most common)
    - `0x3` = HIGH
    - `0x5` = MID
    - `0x9` = LOW
  - Bits 3-0 (low nibble): mode
    - `0xF` = Cool
    - `0xF` followed by trailer `0xE` = Fan-only
- **B2** encodes temperature:
  - Bits 7-4 (high nibble): temp index per a custom table
    - `0x4` = 24°C
    - `0xC` = 25°C
    - `0xD` = 26°C
    - (etc — see below)
  - Bits 3-0 (low nibble): mode/special bits
    - `0x0` typically for cool-mode-with-power
    - `0x4` for fan-only mode (when B1 high nibble matches Coolix Fan flag)

### Temperature index table (Cool mode)

| Temp °C | Hex nibble |
|---|---|
| 17 | `0x0` |
| 18 | `0x1` |
| 19 | `0x3` |
| 20 | `0x2` |
| 21 | `0x6` |
| 22 | `0x7` |
| 23 | `0x5` |
| 24 | `0x4` |
| 25 | `0xC` |
| 26 | `0xD` |
| 27 | `0x9` |
| 28 | `0x8` |
| 29 | `0xA` |
| 30 | `0xB` |

(Confirmed from IRremoteESP8266 source + our captures.)

## Why standard `IRremoteESP8266` decoders may report unexpected values

The standard `decodeCoolix()` in IRremoteESP8266 implements one specific Coolix variant. Some GAir codes don't decode cleanly into mode/temp/fan via that lib — for example `0xB23FC0` which is "Cool 25 Fan HIGH ON" in our captures might decode as something unexpected via the lib.

Don't trust the lib's interpretation. Trust your captures from the physical remote.

## How to add support for other Coolix variants

If your remote produces different codes:

1. Capture your own (see [`03-capture-workflow.md`](03-capture-workflow.md))
2. Decode using [`tools/decode_coolix.py`](../tools/decode_coolix.py)
3. Compare to this table — map your codes to the GAir equivalents OR document a new variant

The bit layout is consistent across Coolix family — only the specific byte values differ. The capture-replay approach works for any variant since it's protocol-agnostic at transmission level.
