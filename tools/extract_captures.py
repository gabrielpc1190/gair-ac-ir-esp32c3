#!/usr/bin/env python3
"""Extract IR captures from a GAir capture-firmware ESP via Home Assistant WebSocket API.

Usage:
    python extract_captures.py --label "cool_25_fan_high" --ha-url https://ha.example.com --token <TOKEN>

Workflow:
    1. Flash gair-ir-capture.yaml to your ESP
    2. In HA, switch ON 'switch.<your_esp>_capture_mode'
    3. Aim physical remote at ESP, press button 5-10 times
    4. Switch OFF capture_mode
    5. Run this script — it'll subscribe to esphome.cap_slot events,
       press the dump button via HA API, and save the captures to JSON

Requirements:
    pip install websocket-client requests

Output:
    Saves to _<label>_captures.json with structure:
        { "0": [4413, -4380, ...], "1": [...], ... }

Then use decode_coolix.py to verify which slot has your desired hex code.
"""

import argparse
import json
import sys
import time

try:
    import requests
    import websocket
    import ssl
except ImportError:
    print("Missing dependencies. Install with: pip install websocket-client requests", file=sys.stderr)
    sys.exit(1)


def extract(ha_url: str, token: str, esp_name: str, label: str, output_path: str | None = None):
    """Extract captures from ESP via HA WebSocket API.

    Args:
        ha_url: Home Assistant base URL, e.g. "https://ha.example.com"
        token: Long-lived access token
        esp_name: ESPHome device name (e.g. "gair-ir-capture")
        label: Label for the captures (used in output filename)
        output_path: Optional explicit output path; defaults to _<label>_captures.json
    """
    output_path = output_path or f"_{label}_captures.json"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "gair-ac-extract/1.0",
    }
    ws_url = ha_url.replace("https://", "wss://").replace("http://", "ws://").rstrip("/") + "/api/websocket"

    print(f"[1/4] Connecting to {ws_url}...")
    ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})
    msg = json.loads(ws.recv())
    if msg.get("type") != "auth_required":
        print(f"Unexpected initial message: {msg}", file=sys.stderr)
        sys.exit(1)
    ws.send(json.dumps({"type": "auth", "access_token": token}))
    auth_resp = json.loads(ws.recv())
    if auth_resp.get("type") != "auth_ok":
        print(f"Auth failed: {auth_resp}", file=sys.stderr)
        sys.exit(1)
    print("[2/4] Authenticated.")

    # Subscribe to capture events
    ws.send(json.dumps({"id": 1, "type": "subscribe_events", "event_type": "esphome.cap_slot"}))
    sub_resp = json.loads(ws.recv())
    if not sub_resp.get("success"):
        print(f"Subscribe failed: {sub_resp}", file=sys.stderr)
        sys.exit(1)
    print("[3/4] Subscribed to esphome.cap_slot events.")

    # Trigger dump button via HA REST API
    button_eid = f"button.{esp_name.replace('-', '_')}_dump_captures"
    print(f"[4/4] Triggering {button_eid}...")
    r = requests.post(
        f"{ha_url.rstrip('/')}/api/services/button/press",
        headers=headers,
        json={"entity_id": button_eid},
    )
    if r.status_code not in (200, 201):
        print(f"  Dump button press failed: HTTP {r.status_code} {r.text[:200]}", file=sys.stderr)
        sys.exit(1)
    print(f"  press → {r.status_code}")

    # Receive events for 12 seconds
    print("Receiving events (12s timeout)...")
    ws.settimeout(13)
    deadline = time.time() + 12
    events = []
    try:
        while time.time() < deadline:
            msg = json.loads(ws.recv())
            if msg.get("type") == "event":
                events.append(msg.get("event", {}).get("data", {}))
    except (websocket.WebSocketTimeoutException, ConnectionError):
        pass

    # Parse and save
    slot_data = {}
    for evt in events:
        slot = evt.get("slot", "?")
        data = evt.get("data", "")
        timings = [int(t) for t in data.split(",") if t.strip()]
        if timings:
            slot_data[slot] = timings

    print(f"\nReceived {len(slot_data)} non-empty slots:")
    for slot in sorted(slot_data, key=int):
        t = slot_data[slot]
        print(f"  slot {slot}: {len(t)} timings, first 6: {t[:6]}")

    with open(output_path, "w") as f:
        json.dump(slot_data, f, indent=2)
    print(f"\nSaved {output_path}")
    print(f"Next step: python decode_coolix.py {output_path}")

    ws.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ha-url", required=True, help="Home Assistant base URL (e.g. https://ha.example.com)")
    parser.add_argument("--token", required=True, help="HA long-lived access token")
    parser.add_argument("--esp-name", default="gair-ir-capture",
                        help="ESPHome device name (default: gair-ir-capture)")
    parser.add_argument("--label", required=True, help="Label for the capture (e.g. 'cool_25_fan_high')")
    parser.add_argument("--output", default=None, help="Explicit output path (default: _<label>_captures.json)")
    args = parser.parse_args()
    extract(args.ha_url, args.token, args.esp_name, args.label, args.output)


if __name__ == "__main__":
    main()
