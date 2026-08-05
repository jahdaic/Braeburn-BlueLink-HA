"""Climate platform for Braeburn BlueLink thermostats."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_ON,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BL_TO_FAN,
    BL_TO_HVAC,
    DOMAIN,
    FAN_CIRCULATE,
    FAN_TO_BL,
    FIELD_COOL_SP,
    FIELD_CURRENT_TEMP,
    FIELD_FAN,
    FIELD_HEAT_SP,
    FIELD_HUMIDITY,
    FIELD_MODE,
    FIELD_RELAYS,
    HVAC_TO_BL,
)
from .coordinator import BlueLinkCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a climate entity per thermostat."""
    coordinator: BlueLinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BraeburnClimate(coordinator, dev["uuid"]) for dev in coordinator.data
    )


class BraeburnClimate(CoordinatorEntity[BlueLinkCoordinator], ClimateEntity):
    """A Braeburn BlueLink thermostat as an HA climate entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_fan_modes = [FAN_AUTO, FAN_ON, FAN_CIRCULATE]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: BlueLinkCoordinator, uuid: str) -> None:
        super().__init__(coordinator)
        self._uuid = uuid
        self._attr_unique_id = uuid

    # --- helpers -----------------------------------------------------------
    @property
    def _device(self) -> dict[str, Any] | None:
        for dev in self.coordinator.data or []:
            if dev.get("uuid") == self._uuid:
                return dev
        return None

    @property
    def _state(self) -> dict[str, Any]:
        dev = self._device
        return dev.get("state_data", {}) if dev else {}

    def _num(self, key: str) -> int | None:
        try:
            return int(self._state.get(key))
        except (TypeError, ValueError):
            return None

    # --- entity metadata ---------------------------------------------------
    @property
    def device_info(self) -> DeviceInfo:
        dev = self._device or {}
        product = dev.get("product") or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._uuid)},
            name=dev.get("name") or "Braeburn Thermostat",
            manufacturer="Braeburn",
            model=product.get("name"),
            serial_number=dev.get("serial_number"),
        )

    @property
    def available(self) -> bool:
        # Available while the last poll succeeded and the device is present.
        # BlueLink's is_online can briefly flip false as the thermostat re-checks
        # in (e.g. right after a command), so we don't null the entity on it —
        # it's surfaced as an attribute instead.
        return bool(super().available and self._device is not None)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        dev = self._device or {}
        return {
            "is_online": dev.get("is_online"),
            "last_seen": dev.get("last_seen"),
        }

    # --- readings ----------------------------------------------------------
    @property
    def current_temperature(self) -> float | None:
        raw = self._num(FIELD_CURRENT_TEMP)
        return raw / 100 if raw is not None else None

    @property
    def current_humidity(self) -> int | None:
        raw = self._num(FIELD_HUMIDITY)
        # 200 (and anything >= 100) means "no humidity sensor"
        return raw if raw is not None and raw < 100 else None

    @property
    def hvac_mode(self) -> HVACMode | None:
        return BL_TO_HVAC.get(self._num(FIELD_MODE))

    @property
    def hvac_action(self) -> HVACAction | None:
        mode = self.hvac_mode
        if mode == HVACMode.OFF:
            return HVACAction.OFF
        # Status_07 is the equipment/relay bitfield: all-zeros => idle, any active
        # bit => the system is running. Bit positions (compressor/fan/heat stages)
        # aren't individually mapped, so we use the mode to pick heating vs cooling.
        # (A continuously-on fan could read as "running"; refine if that proves noisy.)
        relays = str(self._state.get(FIELD_RELAYS, ""))
        running = bool(relays) and set(relays) != {"0"}
        if not running:
            return HVACAction.IDLE
        if mode == HVACMode.COOL:
            return HVACAction.COOLING
        if mode == HVACMode.HEAT:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def fan_mode(self) -> str | None:
        return BL_TO_FAN.get(self._num(FIELD_FAN))

    @property
    def target_temperature(self) -> int | None:
        mode = self.hvac_mode
        if mode == HVACMode.HEAT:
            return self._num(FIELD_HEAT_SP)
        if mode == HVACMode.COOL:
            return self._num(FIELD_COOL_SP)
        return None

    # --- control -----------------------------------------------------------
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        bl = HVAC_TO_BL.get(hvac_mode)
        if bl is not None:
            await self.coordinator.async_set_attr(self._uuid, {FIELD_MODE: bl})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        bl = FAN_TO_BL.get(fan_mode)
        if bl is not None:
            await self.coordinator.async_set_attr(self._uuid, {FIELD_FAN: bl})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        if self.hvac_mode == HVACMode.HEAT:
            await self.coordinator.async_set_attr(
                self._uuid, {FIELD_HEAT_SP: int(temp)}
            )
        elif self.hvac_mode == HVACMode.COOL:
            await self.coordinator.async_set_attr(
                self._uuid, {FIELD_COOL_SP: int(temp)}
            )
