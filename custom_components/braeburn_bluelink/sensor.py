"""Sensor platform for Braeburn BlueLink thermostats.

Exposes the thermostat's readings (temperature, humidity) as standalone sensor
entities. The climate entity already surfaces these as attributes, but a sensor
with ``state_class=measurement`` gets long-term statistics and drops straight
onto a dashboard graph with the built-in cards — no custom frontend needed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BL_MODE_COOL,
    BL_MODE_HEAT,
    DOMAIN,
    FIELD_COOL_SP,
    FIELD_CURRENT_TEMP,
    FIELD_HEAT_SP,
    FIELD_HUMIDITY,
    FIELD_MODE,
)
from .coordinator import BlueLinkCoordinator


def _num(state: dict[str, Any], key: str) -> int | None:
    """Parse an integer reading out of a thermostat's state_data."""
    try:
        return int(state.get(key))
    except (TypeError, ValueError):
        return None


def _current_temperature(state: dict[str, Any]) -> float | None:
    raw = _num(state, FIELD_CURRENT_TEMP)
    return raw / 100 if raw is not None else None


def _current_humidity(state: dict[str, Any]) -> int | None:
    raw = _num(state, FIELD_HUMIDITY)
    # 200 (anything >= 100) means the thermostat has no humidity sensor.
    return raw if raw is not None and raw < 100 else None


def _target_temperature(state: dict[str, Any]) -> int | None:
    # The active setpoint depends on the mode: heat -> heat setpoint,
    # cool -> cool setpoint, off -> no target. Mirrors the climate entity's
    # target_temperature so a "setpoint vs measured" graph lines up.
    mode = _num(state, FIELD_MODE)
    if mode == BL_MODE_HEAT:
        return _num(state, FIELD_HEAT_SP)
    if mode == BL_MODE_COOL:
        return _num(state, FIELD_COOL_SP)
    return None


@dataclass(frozen=True, kw_only=True)
class BraeburnSensorDescription(SensorEntityDescription):
    """Describes a Braeburn sensor and how to read it from state_data."""

    value_fn: Callable[[dict[str, Any]], float | int | None]


SENSORS: tuple[BraeburnSensorDescription, ...] = (
    BraeburnSensorDescription(
        key="current_temperature",
        translation_key="current_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        value_fn=_current_temperature,
    ),
    BraeburnSensorDescription(
        key="current_humidity",
        translation_key="current_humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_current_humidity,
    ),
    BraeburnSensorDescription(
        key="target_temperature",
        translation_key="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        value_fn=_target_temperature,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a sensor per reading, per thermostat."""
    coordinator: BlueLinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BraeburnSensor] = []
    for dev in coordinator.data:
        state = dev.get("state_data", {})
        for description in SENSORS:
            # Don't create a permanently-unknown humidity entity on thermostats
            # that have no humidity sensor.
            if (
                description.key == "current_humidity"
                and description.value_fn(state) is None
            ):
                continue
            entities.append(BraeburnSensor(coordinator, dev["uuid"], description))
    async_add_entities(entities)


class BraeburnSensor(CoordinatorEntity[BlueLinkCoordinator], SensorEntity):
    """A single reading from a Braeburn BlueLink thermostat."""

    _attr_has_entity_name = True
    entity_description: BraeburnSensorDescription

    def __init__(
        self,
        coordinator: BlueLinkCoordinator,
        uuid: str,
        description: BraeburnSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._uuid = uuid
        self.entity_description = description
        self._attr_unique_id = f"{uuid}_{description.key}"

    @property
    def _device(self) -> dict[str, Any] | None:
        for dev in self.coordinator.data or []:
            if dev.get("uuid") == self._uuid:
                return dev
        return None

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
        return bool(super().available and self._device is not None)

    @property
    def native_value(self) -> float | int | None:
        dev = self._device
        state = dev.get("state_data", {}) if dev else {}
        return self.entity_description.value_fn(state)
