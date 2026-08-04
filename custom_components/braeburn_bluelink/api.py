"""Minimal async client for the Braeburn BlueLink cloud API.

The BlueLink Smart Connect web app talks to a Django REST (dj-rest-auth) API:
  POST /rest-auth/login/  {username, password} -> {"key": <token>}
  GET  /devices/                                -> list of devices + state_data
  POST /manage/{uuid}/setstateattr/?wait=True   -> write state attributes
Auth header is "Authorization: Token <key>".
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE

_LOGGER = logging.getLogger(__name__)


class BlueLinkError(Exception):
    """Generic BlueLink API error."""


class BlueLinkAuthError(BlueLinkError):
    """Authentication failed (bad credentials or expired token)."""


class BlueLinkClient:
    """Small wrapper around the BlueLink REST API."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None

    @property
    def token(self) -> str | None:
        """The current auth token, if logged in."""
        return self._token

    async def async_login(self) -> str:
        """Authenticate and cache the token."""
        try:
            async with self._session.post(
                f"{API_BASE}/rest-auth/login/",
                json={"username": self._username, "password": self._password},
            ) as resp:
                data = await resp.json(content_type=None)
                if resp.status in (400, 401, 403):
                    raise BlueLinkAuthError(data)
                resp.raise_for_status()
        except aiohttp.ClientError as err:
            raise BlueLinkError(err) from err

        token = (data or {}).get("key")
        if not token:
            raise BlueLinkAuthError("No token in login response")
        self._token = token
        return token

    async def _headers(self) -> dict[str, str]:
        if not self._token:
            await self.async_login()
        return {"Authorization": f"Token {self._token}"}

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return the list of devices with their current state_data."""
        try:
            async with self._session.get(
                f"{API_BASE}/devices/", headers=await self._headers()
            ) as resp:
                if resp.status == 401:
                    # token expired -> re-login once and retry
                    self._token = None
                    async with self._session.get(
                        f"{API_BASE}/devices/", headers=await self._headers()
                    ) as retry:
                        retry.raise_for_status()
                        return await retry.json(content_type=None)
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise BlueLinkError(err) from err

    async def async_set_state_attr(
        self, uuid: str, payload: dict[str, Any]
    ) -> None:
        """Write one or more state attributes to a device (control)."""
        url = f"{API_BASE}/manage/{uuid}/setstateattr/?wait=True"
        try:
            async with self._session.post(
                url, json=payload, headers=await self._headers()
            ) as resp:
                if resp.status == 401:
                    self._token = None
                    async with self._session.post(
                        url, json=payload, headers=await self._headers()
                    ) as retry:
                        retry.raise_for_status()
                        return
                resp.raise_for_status()
        except aiohttp.ClientError as err:
            raise BlueLinkError(err) from err
