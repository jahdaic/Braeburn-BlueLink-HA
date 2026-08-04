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
# HEAT/COOL are confirmed from the app bundle. AUTO/OFF are best-guess and should
# be verified on a real unit: set each mode in the BlueLink app, then read
# User_Setting_02 with ~/Scripts/bluelink_probe.sh. Update here if they differ.
BL_MODE_AUTO = 0
BL_MODE_HEAT = 1
BL_MODE_COOL = 2
BL_MODE_OFF = 3  # TODO: confirm

BL_TO_HVAC: dict[int, HVACMode] = {
    BL_MODE_OFF: HVACMode.OFF,
    BL_MODE_HEAT: HVACMode.HEAT,
    BL_MODE_COOL: HVACMode.COOL,
    BL_MODE_AUTO: HVACMode.HEAT_COOL,
}
HVAC_TO_BL: dict[HVACMode, int] = {v: k for k, v in BL_TO_HVAC.items()}

# --- fan enum (User_Setting_03) — confirmed ---
FAN_CIRCULATE = "circulate"
BL_FAN_AUTO = 0
BL_FAN_ON = 1
BL_FAN_CIRC = 3

BL_TO_FAN: dict[int, str] = {BL_FAN_AUTO: "auto", BL_FAN_ON: "on", BL_FAN_CIRC: FAN_CIRCULATE}
FAN_TO_BL: dict[str, int] = {v: k for k, v in BL_TO_FAN.items()}
