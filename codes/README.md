# Codes — captured GAir IR signals

## `captures.json`

Master file with 16 verified GAir captures from a physical mini-split remote (Casa GADI installation, captured 2026-05-05).

Each entry has:
- `label`: Human-friendly button name
- `description`: What the button does
- `hex_24bit`: Decoded Coolix 24-bit code (verified against `IRremoteESP8266` reference table)
- `verified_against_expected`: True if hex matches the expected code per our table
- `timings_count`: 200 (Coolix double-frame)
- `timings`: Raw IR pulse durations in microseconds (positive = mark, negative = space)

## How to use

### In ESPHome (production firmware)

Embed the `timings` list directly into a `transmit_raw` button:

```yaml
- platform: template
  name: "AC Cool 25 Fan HIGH"
  on_press:
    - remote_transmitter.transmit_raw:
        code: [4413, -4380, 539, -1639, ...]  # paste from captures.json
        carrier_frequency: 38028Hz
```

**Critical**: do NOT add `repeat:` — the 200 timings are already a complete Coolix double-frame.

### In tests / Python

Decode any capture's hex code with [`tools/decode_coolix.py`](../tools/decode_coolix.py).

### To verify your AC accepts the included codes

If your AC is a GAir or close-variant Coolix model:

1. Flash [`firmware/gair-ir.yaml`](../firmware/gair-ir.yaml) to your ESP
2. Press a button (e.g. "Cool 25 Fan HIGH")
3. Listen — the AC should respond with **a single short beep** identical to your physical remote's beep
4. If you hear **a long two-toned beep**, your AC is a different Coolix variant and you'll need to capture your own. See [`docs/03-capture-workflow.md`](../docs/03-capture-workflow.md).

## Compatibility notes

These captures are confirmed working on:
- GAir 9000 BTU mini-splits (4 units in Casa GADI installation)

They might work on other Coolix-variant ACs (Bosch, some Toshiba, Brisa). If you confirm compatibility with another model, please open an issue/PR.

## Adding your own captures

1. Capture using [`firmware/gair-ir-capture.yaml`](../firmware/gair-ir-capture.yaml)
2. Extract via [`tools/extract_captures.py`](../tools/extract_captures.py)
3. Decode + verify via [`tools/decode_coolix.py`](../tools/decode_coolix.py)
4. Add to `captures.json` following the same JSON schema
5. (Optional) PR with your AC model + verified codes for the community
