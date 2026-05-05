# GAir Air Conditioner + ESP32-C3 IR Control

Reliable IR control of GAir (and similar Coolix-variant) air conditioners using ESPHome on ESP32-C3, via **`transmit_raw` with bit-perfect captures** of the original physical remote.

If you've tried `transmit_pronto` or `climate.coolix` and your AC responds with a **long warning beep** instead of a clean short beep, this repo is for you.

## TL;DR

- **The bug**: ESPHome's `transmit_pronto` quantizes IR pulse timings to integer pronto units (~26µs at 38kHz). GAir ACs validate timings strictly and respond with a **long beep** when timings are slightly off — even though the AC still executes the command.
- **The fix**: capture the ORIGINAL physical remote's IR signal at full resolution (200 pulse timings = complete Coolix double-frame), store it in the ESP's RAM, and replay it byte-for-byte using `transmit_raw`. The AC responds with a **short beep** identical to the physical remote. Bit-perfect emulation.
- **Bonus**: the captured codes are **universal** for GAir family ACs — capture from one remote, use across all your ACs.

## Symptoms this repo solves

Before:
- ❌ AC executes commands but with a long, two-beat beep (warning)
- ❌ Sometimes "intermittent" — works at midnight, doesn't at morning
- ❌ Same code via physical remote works clean, via ESP doesn't

After:
- ✅ Single short acknowledgment beep, identical to physical remote
- ✅ 100% reliable execution
- ✅ Works for ON, OFF, all temperature × fan speed combinations, LCD toggle, Swing

## Repo contents

| Path | Purpose |
|---|---|
| [`docs/01-the-bug.md`](docs/01-the-bug.md) | Why `transmit_pronto` produces long beeps |
| [`docs/02-the-fix.md`](docs/02-the-fix.md) | `transmit_raw` with full Coolix double-frame captures |
| [`docs/03-capture-workflow.md`](docs/03-capture-workflow.md) | How to capture from YOUR physical remote (only needed once for your model) |
| [`docs/04-coolix-protocol.md`](docs/04-coolix-protocol.md) | GAir variant of the Coolix protocol — bit layout |
| [`firmware/gair-ir.yaml`](firmware/gair-ir.yaml) | ESPHome firmware template — 16 working buttons |
| [`firmware/gair-ir-capture.yaml`](firmware/gair-ir-capture.yaml) | Firmware variant with capture-to-RAM mode |
| [`codes/captures.json`](codes/captures.json) | 16 verified GAir captures (decoded hex + raw timings) |
| [`tools/extract_captures.py`](tools/extract_captures.py) | Pull captured timings from ESP via Home Assistant WS API |
| [`tools/decode_coolix.py`](tools/decode_coolix.py) | Decode raw IR timings → 24-bit Coolix hex code |
| [`examples/`](examples/) | Home Assistant dashboard + automation examples |

## Hardware tested

- **ESP**: Seeed XIAO ESP32-C3 (single-core RISC-V) running ESPHome 2026.4.3
- **A/C**: GAir 9000-12000 BTU mini-split (Coolix variant — original control sends 38kHz, double-frame Coolix structure)
- **IR LED**: 940nm typical (any standard IR LED with proper driver works)

The technique generalizes to any ESP32 + any Coolix-variant AC where the physical remote works and `transmit_pronto` produces long beeps.

## Quick start

If your AC is a tested GAir model (or compatible variant):

1. Use [`codes/captures.json`](codes/captures.json) — 16 button captures already done.
2. Adapt [`firmware/gair-ir.yaml`](firmware/gair-ir.yaml): set your WiFi credentials, IP, button list.
3. Compile + flash to your ESP32-C3 (`esphome run gair-ir.yaml --device <IP>`).
4. Add buttons to Home Assistant dashboard.

If your AC is a different model/variant:

1. Flash [`firmware/gair-ir-capture.yaml`](firmware/gair-ir-capture.yaml) (capture-mode firmware).
2. Follow [`docs/03-capture-workflow.md`](docs/03-capture-workflow.md) to record IR signals from your physical remote.
3. Pull captures via [`tools/extract_captures.py`](tools/extract_captures.py).
4. Embed the verified timings into [`firmware/gair-ir.yaml`](firmware/gair-ir.yaml).
5. Compile + flash.

## Background

This work was done while debugging IR control of 4 GAir ACs in a residential offgrid solar+battery installation (Casa GADI, 2026). After multiple sessions chasing hardware/EMI/lockout hypotheses (all wrong), the breakthrough on 2026-05-05 identified pronto quantization as the root cause. Documented exhaustively to save others the same path.

## License

MIT — use freely. Attribution appreciated but not required.

## Contributing

Found this works on another AC model? Open an issue or PR with:
- AC model & manufacturer
- Captured codes (`codes/captures.json` format)
- Any timing differences observed

Goal: build a community library of verified Coolix-variant captures.
