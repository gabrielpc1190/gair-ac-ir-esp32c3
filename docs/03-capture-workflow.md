# Capture Workflow — recording your physical remote

The captures in [`codes/captures.json`](../codes/captures.json) are from one specific GAir remote. Other GAir / Coolix-variant ACs may use slightly different timings or codes. If your AC responds with a long beep using the included codes, capture your own.

## Hardware needed

- ESP32-C3 (or any ESPHome-compatible ESP32) with:
  - IR LED on a GPIO (TX) — typically GPIO3 with proper driver transistor
  - IR receiver IC on another GPIO (RX) — typically GPIO4 with TSOP38xx (38kHz demodulating receiver)
- Original physical remote of your AC

## Step 1: Flash capture firmware

Use [`firmware/gair-ir-capture.yaml`](../firmware/gair-ir-capture.yaml). Adjust:
- `wifi.ssid` / `wifi.password` to your network
- `api.encryption.key` to a unique key
- `wifi.use_address` to the IP you'll OTA-flash to next time

Flash via USB-CDC or Wireless OTA:
```bash
esphome run gair-ir-capture.yaml --device <ESP_IP_OR_/dev/ttyACM0>
```

## Step 2: Set up Home Assistant

Add the ESP to HA via the ESPHome integration. You should see new entities:
- `switch.<your_esp>_capture_mode` — toggle to enter/exit capture mode
- `button.<your_esp>_dump_captures` — emit captured timings as events
- `sensor.<your_esp>_capture_count` — current count of captures stored (0-10)

## Step 3: Capture each button

For EACH button you want (e.g. `Cool 25 Fan HIGH ON`):

### A. Set the remote to the desired state

This is the most error-prone step. The remote's display determines what code each press emits.

For state-encoding buttons (ON/OFF/temperature/fan-speed), the remote sends the FULL state (mode + temp + fan + power). To capture "Cool 25 Fan HIGH ON":

1. Press POWER until the remote display shows ON (any state)
2. Press MODE until display shows COOL
3. Press TEMP+/- until display shows 25°C
4. Press FAN until display shows HIGH (3 bars typically)

For toggle-only buttons (LCD, SWING), the remote sends a fixed code regardless of state — simpler.

### B. Capture

1. Toggle `switch.<esp>_capture_mode` ON in Home Assistant
2. **Aim the remote DIRECTLY at the ESP's IR receiver**, 10-30cm distance (the receiver has a narrow cone)
3. Press the desired button on the remote 5-10 times
4. Watch `sensor.<esp>_capture_count` go up
5. Toggle capture mode OFF

### C. Extract via Home Assistant

Run [`tools/extract_captures.py`](../tools/extract_captures.py):
```bash
python tools/extract_captures.py --label "cool_25_fan_high"
```

This subscribes to `esphome.cap_slot` events, presses the dump button via HA API, and saves the captures to `_<label>_captures.json`.

### D. Verify with hex decode

```bash
python tools/decode_coolix.py _cool_25_fan_high_captures.json
```

Output:
```
slot 0: 0xB23FC0  [Cool 25 fan HIGH]  invOK=True
slot 1: 0xB23FC0  [Cool 25 fan HIGH]  invOK=True
slot 2: 0xB2BFC0  [Cool 25 fan AUTO]  invOK=True   ← oops, FAN button cycled
...
```

If multiple slots have different codes, your remote's FAN button was cycling speeds. Pick the slot whose decoded code matches the expected button.

## Step 4: Common gotcha — pressing FAN cycles speeds

When you press FAN to set Fan HIGH, the press itself sends "now I'm at HIGH". The next press sends "now I'm at AUTO" (or LOW depending on cycle order). If you press FAN 5 times consecutively, you get 5 different codes (one per fan speed visited).

**Solution A (recommended)**: cycle FAN to one BEFORE the target, then press once. That single press = target code. Capture mode stores ALL presses, so do this carefully and pick the right slot.

**Solution B**: use a remote that has direct buttons (some GAir models have separate buttons for each speed — much easier to capture).

**Solution C**: use a non-cycling button to send current state — for example, the SWING toggle on some remotes ALSO re-sends the current state code as part of the same transmission.

## Step 5: Embed in firmware

Add the verified capture's raw timings to your `gair-ir.yaml` as a `transmit_raw` button:

```yaml
- platform: template
  name: "AC Cool 25 Fan HIGH"
  on_press:
    - remote_transmitter.transmit_raw:
        code: [4413, -4380, 539, -1639, ...]
        carrier_frequency: 38028Hz
```

Expected timings format:
- Positive number = mark (LED on)
- Negative number = space (LED off)
- Total length: ~200 timings for one Coolix double-frame
- Final value typically `-25000` (long gap before any potential repeat)

## Step 6: Validate

Flash and press the button. Listen:
- ✅ Short beep + AC executes → success
- ❌ Long beep + AC executes → timing not bit-perfect; recapture or check carrier
- ❌ No beep, no execution → frame incomplete or wrong code; check decoded hex

## Tips

- Capture in a quiet IR environment (no other remotes operating, no fluorescent lights flickering)
- The receiver IC has limited angle — keep remote pointed directly at the IC's lens
- 5 captures is enough for variance check; 10 is generous
- Variance >50µs in any pulse position suggests the remote moved during capture or there's IR noise
