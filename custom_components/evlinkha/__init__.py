# custom_components/evlinkha/__init__.py

import logging
from datetime import timedelta
import voluptuous as vol
from aiohttp import web

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.webhook import async_register, async_unregister

from .const import (
    DOMAIN, ENVIRONMENTS,
    CONF_API_KEY, CONF_ENVIRONMENT, CONF_VEHICLE_ID, CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from .api import EVLinkHAClient

_LOGGER = logging.getLogger(__name__)


async def _handle_push_webhook(hass, webhook_id: str, request) -> web.Response:
    """Push webhook for EVLinkHA – updates the vehicle coordinator."""
    try:
        data = await request.json()
        _LOGGER.debug("Push payload: %s", data)

        coord = hass.data.get(DOMAIN, {}).get(f"{webhook_id}_vehicle")
        old = coord.data or {}

        # Start with a copy of the old values
        merged = old.copy()

        # Merge incoming data
        for key, val in data.items():
            # If the value is a dict and we already have a dict under the same key → merge level 2
            if isinstance(val, dict) and isinstance(old.get(key), dict):
                nested = old.get(key, {}).copy()
                nested.update(val)
                merged[key] = nested
            else:
                # Otherwise replace or add
                merged[key] = val

        # Submit the merged data
        coord.async_set_updated_data(merged)

        return web.Response(status=200, text="OK")

    except Exception:
        _LOGGER.exception("Error in push webhook handler")
        return web.Response(status=500, text="Error")


# ... (allt före är oförändrat!)

async def async_setup_entry(hass, entry) -> bool:
    """
    Set up EVLinkHA:
      • DataUpdateCoordinators (userinfo & vehicle status)
      • Charging-service
      • Push-webhook
    """
    _LOGGER.debug("Starting async_setup_entry for %s", entry.entry_id)

    try:
        # Read configuration
        api_key    = entry.data[CONF_API_KEY]
        env        = entry.data.get(CONF_ENVIRONMENT, "sandbox")
        vehicle_id = entry.data[CONF_VEHICLE_ID]
        base_url   = ENVIRONMENTS[env]
        vehicle_poll_minutes = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        _LOGGER.info("---- [EVLinkHA] async_setup_entry called ----")
        _LOGGER.info("Config: api_key=%s, env=%s, vehicle_id=%s, vehicle_poll_minutes=%s", api_key, env, vehicle_id, vehicle_poll_minutes)

        # Initialize API client
        client = EVLinkHAClient(hass, api_key, base_url, vehicle_id)
        _LOGGER.debug("EVLinkHAClient created")

        # 1) User info coordinator (refresh every 5 minutes)
        user_coord = DataUpdateCoordinator(
            hass, _LOGGER,
            name=f"{DOMAIN} user info",
            update_method=client.async_get_userinfo,
            update_interval=timedelta(minutes=vehicle_poll_minutes),
        )
        _LOGGER.debug("User DataUpdateCoordinator created (interval: %s min)", vehicle_poll_minutes)
        await user_coord.async_config_entry_first_refresh()

        # 2) Vehicle status coordinator (refresh every minute)
        vehicle_coord = DataUpdateCoordinator(
            hass, _LOGGER,
            name=f"{DOMAIN} vehicle status",
            update_method=client.async_get_vehicle_status,
            update_interval=timedelta(minutes=vehicle_poll_minutes),
        )
        _LOGGER.debug("Vehicle DataUpdateCoordinator created (interval: %s min)", vehicle_poll_minutes)
        await vehicle_coord.async_config_entry_first_refresh()

        # Store coordinators
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = user_coord
        hass.data[DOMAIN][f"{entry.entry_id}_vehicle"] = vehicle_coord
        _LOGGER.debug("Coordinators stored in hass.data for entry %s", entry.entry_id)

        # 3) Register charging service
        schema = vol.Schema({vol.Required("action"): vol.In(["START", "STOP"])})
        async def _handle_charging(call):
            action = call.data["action"]
            _LOGGER.debug("Service set_charging called with action=%s", action)
            try:
                result = await client.async_set_charging(action)
                if result:
                    _LOGGER.info("Charging %s executed successfully", action)
                else:
                    _LOGGER.error("Charging %s failed or returned None", action)
            except Exception as e:
                _LOGGER.exception("Error in set_charging service")

        hass.services.async_register(
            DOMAIN,
            "set_charging",
            _handle_charging,
            schema=schema,
        )
        _LOGGER.debug("Service set_charging registered")

        # 4) Register webhook under /api/webhook/{entry_id}
        webhook_id = entry.entry_id
        async_register(
            hass,
            DOMAIN,
            "EVLinkHA Push",
            webhook_id,
            _handle_push_webhook,
        )
        _LOGGER.debug("Webhook registered with id=%s", webhook_id)

        # 5) Forward to the sensor platform
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
        _LOGGER.debug("Forwarded entry to sensor platform")

        _LOGGER.info("---- [EVLinkHA] async_setup_entry finished for %s ----", entry.entry_id)
        return True

    except Exception:
        _LOGGER.exception("Error setting up EVLinkHA integration")
        return False

async def async_unload_entry(hass, entry) -> bool:
    """Unload EVLinkHA: deregister webhook & service, remove coordinators."""
    _LOGGER.debug("Unloading EVLinkHA entry %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    hass.services.async_remove(DOMAIN, "set_charging")
    async_unregister(hass, entry.entry_id)
    _LOGGER.debug("Service and webhook unregistered")
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    hass.data.get(DOMAIN, {}).pop(f"{entry.entry_id}_vehicle", None)
    return unload_ok

# Lägg till denna!
async def async_reload_entry(hass, entry):
    """Reload EVLinkHA config entry when options are updated."""
    _LOGGER.info("---- [EVLinkHA] async_reload_entry called for %s ----", entry.entry_id)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
    _LOGGER.info("---- [EVLinkHA] async_reload_entry finished for %s ----", entry.entry_id)
