# Braeburn BlueLink — Home Assistant integration

An unofficial [Home Assistant](https://www.home-assistant.io/) custom integration for **Braeburn
BlueLink Smart Connect** Wi-Fi thermostats. It adds each thermostat as a `climate` entity you can
read and control, using the same cloud API as the BlueLink app.

> ⚠️ **Unofficial / unaffiliated.** Not endorsed by Braeburn Systems. The cloud API was
> reverse-engineered from the BlueLink web app and may change without notice. Use at your own risk.

## Features

- Auto-discovers the thermostats on your BlueLink account
- **Reads:** current temperature, heat/cool setpoints, mode, fan mode, humidity (if the unit has a
  sensor), online status
- **Controls:** HVAC mode, heat/cool setpoints, fan mode
- Simple UI setup (email + password) — no YAML

## Requirements

- A Braeburn BlueLink thermostat already set up in the **BlueLink Smart Connect** app
- Home Assistant 2024.1 or newer

## Installation

### HACS (recommended)
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/jahdaic/Braeburn-BlueLink-HA`,
   category **Integration**.
2. Install **Braeburn BlueLink**, then restart Home Assistant.
3. **Settings → Devices & Services → + Add Integration → Braeburn BlueLink**, and sign in with your
   BlueLink email and password.

### Manual
Copy `custom_components/braeburn_bluelink/` into your Home Assistant `config/custom_components/`
directory, restart, then add the integration as above.

## Notes & limitations

- **Cloud polling** (default every 120 s). Braeburn has no documented local API.
- **Mode values:** `heat` and `cool` are confirmed; `auto` and `off` are best-guess defaults that
  may differ per model. If your thermostat's Off/Auto don't behave, set each mode in the BlueLink
  app and read back `User_Setting_02` (see the probe script referenced in the docs), then adjust
  the values in `const.py` and open an issue/PR with your findings.
- Temperatures are handled in **°F** (matching the BlueLink API); HA will convert for display.

## How it works

The BlueLink web app is an Angular SPA that talks to a Django REST (`dj-rest-auth`) API at
`sd2.bluelinksmartconnect.com`. This integration logs in for a token, polls `GET /devices/` for
state, and writes control changes to `POST /manage/{uuid}/setstateattr/`. The device state lives in
a `state_data` dict of opaque keys (`Status_01`, `User_Setting_04`, …) which this integration maps
to standard climate attributes.

## Contributing

Issues and PRs welcome — especially confirmed mode/fan enum values for different Braeburn models.

## License

[MIT](LICENSE) © 2026 Jahdai Cintron
