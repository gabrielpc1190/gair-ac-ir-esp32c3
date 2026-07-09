---
type: project
title: gair-ac-esp32c3
description: "Firmware ESPHome (ESP32-C3) para control IR de aires acondicionados GAir (variante Coolix), 16 botones expuestos a HA."
production: false
status: active
stack: [esphome, esp32]
repo: "git@github.com:gabrielpc1190/gair-ac-ir-esp32c3.git"
tags: [gadi, domotica, firmware]
related: [HomeAssistant, bluesun-bms-esp32s3-panel]
---

# CLAUDE.md — gair-ac-esp32c3

> Firmware ESPHome para ESP32-C3 (Seeed XIAO) que controla aires acondicionados **GAir** (variante Coolix) por IR. Funciona y está documentado. Respaldo: **GitHub** `git@github.com:gabrielpc1190/gair-ac-ir-esp32c3.git` (ojo: el repo se llama `gair-ac-ir-esp32c3`, la carpeta `gair-ac-esp32c3`).

## Cómo compilar/flashear

```bash
esphome compile firmware/gair-ir.yaml
esphome run firmware/gair-ir.yaml --device <ESP_IP_OR_/dev/ttyACM0>
```

Primer flash por USB (`/dev/ttyACM0`); luego OTA por IP. Antes hay que crear `firmware/secrets.yaml` (ver `secrets.yaml.example`).

## Mapa

- **`firmware/gair-ir.yaml`** — firmware de producción. Board `seeed_xiao_esp32c3`, framework `esp-idf` (BT y IPv6 deshabilitados). Expone a Home Assistant **16 `button` template** (ON Cool 25 Fan HIGH, OFF, Fan-only LOW/HIGH, Cool 24/25/26°C × Fan LOW/MID/HIGH + Cool 25 AUTO, LCD Toggle, Swing Toggle) + un `light` Status LED. Pines: **GPIO3 = IR TX**, **GPIO4 = IR RX**, GPIO7 = status LED. API encriptada + OTA, ambos vía `!secret`.
- **`firmware/gair-ir-capture.yaml`** — variante en modo captura-a-RAM, para grabar botones nuevos desde tu control físico.
- **`firmware/secrets.yaml.example`** — plantilla: `wifi_ssid`, `wifi_password`, `api_encryption_key`, `ota_password`, `fallback_ap_password`. Copiar a `secrets.yaml` (gitignored).
- **`codes/captures.json`** — los 16 capturas verificadas (hex Coolix + timings raw).
- **`tools/`** — `extract_captures.py` (saca timings del ESP vía HA WS API), `decode_coolix.py` (timings → hex 24-bit).
- **`examples/`** — dashboard y automatizaciones de Home Assistant de ejemplo.

## Gotchas / contexto no-obvio

- **No usar `transmit_pronto` ni `climate.coolix`**: el GAir valida timings estrictamente y responde con un **beep largo de advertencia**. La solución es `transmit_raw` con capturas bit-perfect del control físico (200 timings = doble-frame Coolix completo) → beep corto idéntico al original. Es el motivo de existir del repo.
- **No agregar `repeat:`** a los botones: las capturas ya incluyen el doble-frame.
- `wifi.power_save_mode: NONE` y `remote_transmitter.non_blocking: false` son **críticos** para evitar jitter de RMT/WiFi durante el TX.
- Para capturar botones nuevos (otros temps/modos/marcas) está el flujo en `docs/03-capture-workflow.md`.
- Contexto: nació depurando 4 ACs GAir en Casa GADI (instalación solar offgrid, 2026).

## Más

- **[README.md](README.md)** — guía completa: bug, fix, cobertura de los 16 botones, hardware probado.
- **[docs/](docs/)** — `01-the-bug.md`, `02-the-fix.md`, `03-capture-workflow.md`, `04-coolix-protocol.md`.
