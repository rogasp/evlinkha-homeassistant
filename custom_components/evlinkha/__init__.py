# custom_components/evlinkha/__init__.py

import logging
from datetime import timedelta
import voluptuous as vol
from aiohttp import web

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.webhook import async_register, async_unregister

from .const import (
    DOMAIN, ENVIRONMENTS,
    CONF_API_KEY, CONF_ENVIRONMENT, CONF_VEHICLE_ID,
)
from .api import EVLinkHAClient

_LOGGER = logging.getLogger(__name__)


async def _handle_push_webhook(hass, webhook_id: str, request) -> web.Response:
    """Push-webhook för EVLinkHA – uppdaterar vehicle-coordinator."""
    try:
        data = await request.json()
        _LOGGER.debug("Push payload: %s", data)

        coord = hass.data.get(DOMAIN, {}).get(f"{webhook_id}_vehicle")
        old = coord.data or {}

        # Starta med en kopia av gamla värden
        merged = old.copy()

        # Gå igenom incoming och slå ihop
        for key, val in data.items():
            # Om värdet är ett dict och vi redan har ett dict under samma nyckel → mergerar nivå 2
            if isinstance(val, dict) and isinstance(old.get(key), dict):
                nested = old.get(key, {}).copy()
                nested.update(val)
                merged[key] = nested
            else:
                # Annars ersätt eller lägg till
                merged[key] = val

        # Skicka in den sammanslagna datan
        coord.async_set_updated_data(merged)

        return web.Response(status=200, text="OK")

    except Exception:
        _LOGGER.exception("Error in push webhook handler")
        return web.Response(status=500, text="Error")


async def async_setup_entry(hass, entry) -> bool:
    """
    Set up EVLinkHA:
      • DataUpdateCoordinators (userinfo & vehicle status)
      • Charging-service
      • Push-webhook
    """
    _LOGGER.debug("Starting async_setup_entry for %s", entry.entry_id)
    try:
        # Läs in konfig
        api_key    = entry.data[CONF_API_KEY]
        env        = entry.data.get(CONF_ENVIRONMENT, "prod")
        vehicle_id = entry.data[CONF_VEHICLE_ID]
        base_url   = ENVIRONMENTS[env]
        _LOGGER.debug("Config: api_key=%s, env=%s, vehicle_id=%s", api_key, env, vehicle_id)

        # Initiera API-klient
        client = EVLinkHAClient(hass, api_key, base_url, vehicle_id)

        # 1) User info coordinator (uppdatera var 5:e minut)
        user_coord = DataUpdateCoordinator(
            hass, _LOGGER,
            name=f"{DOMAIN} user info",
            update_method=client.async_get_userinfo,
            update_interval=timedelta(minutes=5),
        )
        await user_coord.async_config_entry_first_refresh()

        # 2) Vehicle status coordinator (uppdatera var minut)
        vehicle_coord = DataUpdateCoordinator(
            hass, _LOGGER,
            name=f"{DOMAIN} vehicle status",
            update_method=client.async_get_vehicle_status,
            update_interval=timedelta(minutes=1),
        )
        await vehicle_coord.async_config_entry_first_refresh()

        # Spara coordinators
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = user_coord
        hass.data[DOMAIN][f"{entry.entry_id}_vehicle"] = vehicle_coord

        # 3) Registrera charging-service
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

        # 4) Registrera webhook under /api/webhook/{entry_id}
        webhook_id = entry.entry_id
        async_register(
            hass,
            DOMAIN,
            "EVLinkHA Push",
            webhook_id,
            _handle_push_webhook,
        )
        _LOGGER.debug("Webhook registered with id=%s", webhook_id)

        # 5) Forwarda till sensor-plattformen
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
        _LOGGER.debug("Forwarded entry to sensor platform")

        return True

    except Exception:
        _LOGGER.exception("Error setting up EVLinkHA integration")
        return False


async def async_unload_entry(hass, entry) -> bool:
    """Unload EVLinkHA: deregister webhook & service, ta bort coordinators."""
    _LOGGER.debug("Unloading EVLinkHA entry %s", entry.entry_id)
    # Avregistrera sensorer
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])

    # Avregistrera service och webhook
    hass.services.async_remove(DOMAIN, "set_charging")
    async_unregister(hass, entry.entry_id)
    _LOGGER.debug("Service and webhook unregistered")

    # Rensa data
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    hass.data.get(DOMAIN, {}).pop(f"{entry.entry_id}_vehicle", None)

    return unload_ok
