"""DataUpdateCoordinator for Braeburn BlueLink."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BlueLinkClient, BlueLinkError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BlueLinkCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Polls the BlueLink API for device state and pushes control writes."""

    def __init__(self, hass: HomeAssistant, client: BlueLinkClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            return await self.client.async_get_devices()
        except BlueLinkError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_attr(self, uuid: str, payload: dict[str, Any]) -> None:
        """Write attributes to a device, then refresh state."""
        await self.client.async_set_state_attr(uuid, payload)
        await self.async_request_refresh()
