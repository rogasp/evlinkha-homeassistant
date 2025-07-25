"""
EVLinkHA API client for fetching user and vehicle information and 
handling rate‐limit (HTTP 429) with persistent notifications.
"""
from datetime import datetime
import aiohttp
import logging

from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)

class EVLinkHAClient:
    """
    HTTP client to interact with EVLinkHA backend.

    Args:
      hass: Home Assistant core instance (for notifications).
      api_key (str): Bearer token.
      base_url (str): Base URL of the EVLinkHA API.
      vehicle_id (str): ID of the vehicle for status/charge endpoints.
    """
    def __init__(self, hass, api_key: str, base_url: str, vehicle_id: str):
        self.hass       = hass
        self.api_key    = api_key
        self.base_url   = base_url.rstrip("/")
        self.vehicle_id = vehicle_id

    async def async_get_userinfo(self) -> dict | None:
        url = f"{self.base_url}/api/v1/ha/me"
        headers = {"X-API-Key": f"{self.api_key}"}
        _LOGGER.debug(f"[EVLinkHAClient] GET userinfo: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        _LOGGER.debug(f"[EVLinkHAClient] Userinfo: {data}")
                        return data

                    _LOGGER.error(f"[EVLinkHAClient] Failed userinfo: HTTP {resp.status}")
        except Exception as err:
            _LOGGER.exception(f"[EVLinkHAClient] Exception fetching userinfo: {err}")
        return None

    async def async_get_vehicle_status(self) -> dict:
        """
        Fetch full status for the configured vehicle.
        Raises UpdateFailed on rate‐limit (429) to skip this cycle.
        """
        _LOGGER.info("Polling vehicle status at %s", datetime.now())
        url = f"{self.base_url}/api/v1/ha/status/{self.vehicle_id}"
        headers = {"X-API-Key": f"{self.api_key}"}
        _LOGGER.debug(f"[EVLinkHAClient] GET vehicle status: {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        _LOGGER.debug(f"[EVLinkHAClient] Vehicle status: {data}")
                        return data

                    if resp.status == 429:
                        _LOGGER.warning(f"[EVLinkHAClient] Rate limited (429) on {url}")
                        self.hass.async_create_task(
                            self.hass.services.async_call(
                                "persistent_notification",
                                "create",
                                {
                                    "title": "EVLinkHA Rate Limit",
                                    "message": (
                                        f"Rate limit hit for vehicle {self.vehicle_id}. "
                                        "Skipping this update."
                                    ),
                                },
                            )
                        )
                        raise UpdateFailed("429 rate limited by EVLinkHA")
                    
                    # Bad request (e.g. invalid vehicle_id, backend error, etc)
                    if resp.status == 400:
                        text = await resp.text()
                        _LOGGER.warning(f"[EVLinkHAClient] Vehicle status fetch rejected (400): {text}")
                        self.hass.async_create_task(
                            self.hass.services.async_call(
                                "persistent_notification",
                                "create",
                                {
                                    "title": "EVLinkHA Vehicle Status Error",
                                    "message": (
                                        f"Vehicle status request rejected for vehicle {self.vehicle_id}. "
                                        f"Error: {text}"
                                    ),
                                },
                            )
                        )
                        return None

                    # Other errors
                    text = await resp.text()
                    _LOGGER.error(f"[EVLinkHAClient] Vehicle status fetch failed HTTP {resp.status}: {text}")
                    self.hass.async_create_task(
                        self.hass.services.async_call(
                            "persistent_notification",
                            "create",
                            {
                                "title": "EVLinkHA Vehicle Status Error",
                                "message": (
                                    f"Unexpected error {resp.status} when trying to fetch vehicle status."
                                ),
                            },
                        )
                    )
                    return None

        except Exception as err:
            _LOGGER.exception(f"[EVLinkHAClient] Exception fetching vehicle status: {err}")
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "EVLinkHA Vehicle Status Exception",
                        "message": str(err),
                    },
                )
            )
            return None

    async def async_set_charging(self, action: str) -> dict | None:
        url = f"{self.base_url}/api/v1/ha/charging/{self.vehicle_id}"
        headers = {
            "X-API-Key": f"{self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"action": action.upper()}
        _LOGGER.debug(f"[EVLinkHAClient] POST charging: {url} payload={payload}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=15) as resp:
                    text = await resp.text()
                    if resp.status in (200, 201):
                        data = await resp.json()
                        _LOGGER.debug(f"[EVLinkHAClient] Charging response: {data}")
                        return data
                    _LOGGER.error(
                        f"[EVLinkHAClient] Charging failed HTTP {resp.status}: {text}"
                    )
        except Exception as err:
            _LOGGER.exception(f"[EVLinkHAClient] Exception setting charging: {err}")
        return None

    async def async_get_vehicles(self) -> list[dict]:
        """
        Fetch all vehicles linked to the current user.
        Returns a list of dicts (id, displayName, model, etc), or empty list.
        """
        url = f"{self.base_url}/api/v1/ha/vehicles"
        headers = {"X-API-Key": f"{self.api_key}"}
        _LOGGER.debug(f"[EVLinkHAClient] GET vehicles: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        _LOGGER.debug(f"[EVLinkHAClient] Vehicles: {data}")
                        # Expects: [{"id": "...", "displayName": "...", ...}, ...]
                        return data if isinstance(data, list) else []
                    _LOGGER.error(f"[EVLinkHAClient] Failed to get vehicles: HTTP {resp.status}")
        except Exception as err:
            _LOGGER.exception(f"[EVLinkHAClient] Exception fetching vehicles: {err}")
        return []

