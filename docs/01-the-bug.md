# The Bug — `transmit_pronto` and the GAir long beep

## Symptom

You set up an ESP32-C3 with ESPHome and use `transmit_pronto` (or `climate.coolix`) to control a GAir AC. The AC executes the commands BUT:

- The acknowledgment beep is **long and two-toned** (`beeeeeep-beeeep`) instead of the short single tone (`beep`) you hear from the physical remote
- Sometimes the AC seems to ignore commands intermittently
- Works at low load, fails under high WiFi traffic

You've probably tried:
- `non_blocking: false` — helped reliability but didn't fix the beep
- `power_save_mode: NONE` — same
- Different repeat counts (`repeat: 5 wait_time: 100ms` was a popular workaround)
- Different carrier frequencies (36/38/40 kHz) — no improvement
- Cycling LCD/SWING toggles before commands as "wake" sequences — no improvement
- Capturing your own remote and re-encoding to pronto — same beep

## Root cause

ESPHome's `transmit_pronto` action takes a Pronto Hex code and converts it to RMT pulses for the ESP32 IR carrier modulator. **Pronto encoding quantizes pulse durations to integer multiples of the carrier period (~26.32µs at 38kHz)**.

For example, a Coolix bit-1 has a typical mark of 530µs and a space of 1640µs:
- 530µs ÷ 26.32µs/unit ≈ 20.13 → rounded to 20 units (526µs) — **loss of 4µs**
- 1640µs ÷ 26.32µs/unit ≈ 62.31 → rounded to 62 units (1632µs) — **loss of 8µs**

These quantization losses are within the Coolix protocol tolerance (which is why the AC still executes), but the GAir's IR receiver has a **stricter timing validation that flags out-of-spec timings with a long warning beep**.

The original physical remote sends pulses at sub-microsecond resolution. The ESP's RMT can transmit at the same resolution IF given the raw values. But pronto encoding is the bottleneck.

## Diagnostic test

Set up listen-mode on your ESP and capture the original remote (we'll explain how in [`03-capture-workflow.md`](03-capture-workflow.md)). Then compare:

```python
# Original remote (raw):
[4413, -4380, 539, -1639, 537, -557, 535, -1646, ...]

# Pronto-encoded version (quantized):
[4376, -4376, 526, -1632, 526, -526, 526, -1632, ...]
```

Differences of 4-12µs per pulse. Within Coolix tolerance, outside GAir strict spec.

## Why other ACs don't show this

Most Coolix-variant ACs (some Toshiba, Bosch, Brisa, etc.) accept pronto-quantized timings without complaint. **GAir's specific receiver firmware is stricter**. Other ACs in your house using IR may work fine with pronto — only the GAir flags it.

## Why the historical "T09" technique helped (partially)

`transmit_pronto` with `repeat: 5 wait_time: 100ms` (the so-called T09 technique) sends the pronto-quantized code 5 times. Sometimes one of the 5 retries lines up close enough that the AC accepts it cleanly. But the long beep persists in most cases — T09 was a reliability boost, not a precision fix.

## Why `transmit_raw` with INCOMPLETE captures fails

A common attempt: capture the IR with `remote_receiver` and feed the captured timings into `transmit_raw`. Often this fails (AC doesn't react at all) because the captured frame is **incomplete**. Coolix sends:

```
[header][24 bits][24 bits inverted][gap][header][24 bits][24 bits inverted]
```

That's 200 timings total. If your capture only has 99 timings (one half), `transmit_raw` sends an incomplete Coolix message and the AC ignores it.

## The cure

Capture the FULL 200-timing Coolix double-frame from the physical remote, store it in ESP RAM, and replay with `transmit_raw`. See [`02-the-fix.md`](02-the-fix.md).
