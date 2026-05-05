# The Fix — `transmit_raw` with full Coolix double-frame captures

## Strategy

1. Capture the IR signal from the physical remote at full timing resolution.
2. Make sure the capture includes the **complete Coolix double-frame** (200 timings).
3. Store the captures on the ESP itself (not in HA logs — that path has gotchas).
4. Embed the captured timings into your firmware as `transmit_raw.code:`.

The ESP's RMT TX peripheral can output pulses at sub-microsecond precision, matching the physical remote. No quantization loss → no warning beep.

## Implementation

### Firmware section: capture-to-RAM

```yaml
globals:
  - id: capture_active
    type: bool
    initial_value: 'false'
  - id: capture_count
    type: int
    initial_value: '0'
  - id: capture_buffer
    type: std::string[10]   # 10 slots, each ~1KB CSV string

remote_receiver:
  id: rcvr
  pin:
    number: GPIO4
    inverted: true
    mode: { input: true, pullup: true }
  idle: 25ms
  tolerance: 30%
  on_raw:
    then:
      - if:
          condition:
            lambda: 'return id(capture_active);'
          then:
            - lambda: |-
                if (x.size() < 30) return;
                if (id(capture_count) >= 10) {
                  id(capture_active) = false;
                  return;
                }
                std::string s;
                for (auto t : x) {
                  char b[12]; snprintf(b, sizeof(b), "%d,", t); s += b;
                }
                id(capture_buffer)[id(capture_count)] = s;
                id(capture_count) += 1;
                ESP_LOGW("CAP", "stored %d/10", id(capture_count));

switch:
  - platform: template
    name: "Capture mode"
    optimistic: true
    turn_on_action:
      - lambda: |-
          id(capture_count) = 0;
          for (int i=0; i<10; i++) id(capture_buffer)[i] = "";
          id(capture_active) = true;
    turn_off_action:
      - lambda: 'id(capture_active) = false;'
```

### Firmware section: dump captures via Home Assistant events

Why events? Direct text_sensors are limited to 255 chars. ESPHome logs over WS API are rate-limited. `homeassistant.event` is reliable for variable-size payloads.

```yaml
button:
  - platform: template
    name: "Dump captures"
    on_press:
      - repeat:
          count: 10
          then:
            - homeassistant.event:
                event: esphome.cap_slot
                data:
                  slot: !lambda 'return std::to_string(iteration);'
                  data: !lambda 'return id(capture_buffer)[iteration];'
            - delay: 80ms
```

### Python: extract via WS API

```python
ws.send({'type':'subscribe_events', 'event_type':'esphome.cap_slot'})
# Trigger dump button via API, receive 10 events with full timings
events = []
while time.time() < deadline:
    msg = ws.recv()
    if msg.get('type')=='event':
        events.append(msg['event']['data'])
```

### Production firmware: replay with `transmit_raw`

```yaml
remote_transmitter:
  id: tx
  pin: GPIO3
  carrier_duty_percent: 50%
  non_blocking: false   # critical: blocking ensures full frame transmits without WiFi interference

button:
  - platform: template
    name: "AC ON Cool 25 Fan HIGH"
    on_press:
      - remote_transmitter.transmit_raw:
          code: [4413, -4380, 539, -1639, 537, -557, ...]   # 200 timings from capture
          carrier_frequency: 38028Hz
```

**Critical**: do NOT use `repeat:` with the 200-timing capture — the captured timings ALREADY include the Coolix double-frame structure. Adding `repeat: 5` would send 10 frames total, which the AC interprets as "key held down" and may give a long beep.

## Why this works

1. **Bit-perfect timing**: ESP RMT outputs the EXACT pulse durations from the capture, no quantization.
2. **Complete frame**: 200 timings = Coolix `[hdr][24+24inv][gap][hdr][24+24inv][end]`, exactly what the AC expects.
3. **Carrier matches**: 38028 Hz (ESPHome default for 0x6D pronto unit) matches the physical remote's carrier within tolerance.

## Verification

After flashing the new firmware, press a button and listen:
- Short single beep = ✅ AC accepted the code as bit-perfect-equivalent to the physical remote
- Long two-toned beep = ❌ something is still off (timing, frame structure, or carrier)
- No beep = ❌ frame is too incomplete or carrier wrong

## Reliability

In our deployment (4 AC units, ~1000 button presses over 2 weeks):
- Short beep rate: 100% (vs ~95% for `transmit_pronto repeat:5`)
- Execution rate: 100% (vs ~95-100% depending on conditions)
- Variance between captures: pulse timing varies <10µs across 10 captures of the same button — well within Coolix tolerance, AC accepts all consistently
