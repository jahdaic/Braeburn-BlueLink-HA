"""Constants for the Braeburn BlueLink integration."""

from __future__ import annotations

from homeassistant.components.climate import HVACMode

DOMAIN = "braeburn_bluelink"
API_BASE = "https://sd2.bluelinksmartconnect.com/api/v1/braeburn"
DEFAULT_SCAN_INTERVAL = 120  # seconds

# --- device state_data field keys (reverse-engineered from the BlueLink web app) ---
FIELD_CURRENT_TEMP = "Status_01"        # value / 100 = °F
FIELD_HEAT_SP = "User_Setting_04"       # °F
FIELD_COOL_SP = "User_Setting_05"       # °F
FIELD_MODE = "User_Setting_02"          # system mode enum (below)
FIELD_FAN = "User_Setting_03"           # fan enum (below)
FIELD_HUMIDITY = "Status_03"            # % RH (200 = no humidity sensor)

# --- system mode enum (User_Setting_02) ---
# Confirmed on a BRA7205: 0=OFF, 1=HEAT, 2=COOL. This model has no Auto/changeover
# mode. Other Braeburn models may expose Auto (value unconfirmed — likely 3); if
# yours does, add it here and to BL_TO_HVAC with HVACMode.HEAT_COOL.
BL_MODE_OFF = 0
BL_MODE_HEAT = 1
BL_MODE_COOL = 2

BL_TO_HVAC: dict[int, HVACMode] = {
    BL_MODE_OFF: HVACMode.OFF,
    BL_MODE_HEAT: HVACMode.HEAT,
    BL_MODE_COOL: HVACMode.COOL,
}
HVAC_TO_BL: dict[HVACMode, int] = {v: k for k, v in BL_TO_HVAC.items()}

# --- fan enum (User_Setting_03) — confirmed ---
FAN_CIRCULATE = "circulate"
BL_FAN_AUTO = 0
BL_FAN_ON = 1
BL_FAN_CIRC = 3

BL_TO_FAN: dict[int, str] = {BL_FAN_AUTO: "auto", BL_FAN_ON: "on", BL_FAN_CIRC: FAN_CIRCULATE}
FAN_TO_BL: dict[str, int] = {v: k for k, v in BL_TO_FAN.items()}
