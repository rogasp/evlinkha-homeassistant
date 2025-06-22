# custom_components/evlinkha/config_flow.py

from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN, CONF_API_KEY, CONF_ENVIRONMENT, CONF_VEHICLE_ID, CONF_UPDATE_INTERVAL

DEFAULT_UPDATE_INTERVAL = 6

class EvlinkhaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EVLinkHA."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Initial setup step."""
        if user_input is not None:
            return self.async_create_entry(title="EVLinkHA", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_ENVIRONMENT, default="prod"): vol.In(["prod"]),
                vol.Required(CONF_VEHICLE_ID): str,
            })
        )

    async def async_step_reconfigure(self, user_input=None):
        """Reconfigure main settings after install."""
        entry = self._async_current_entries()[0] if self._async_current_entries() else None
        data = entry.data if entry else {}

        if user_input is not None:
            # Update the config entry data
            return self.async_create_entry(title="EVLinkHA", data=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY, default=data.get(CONF_API_KEY, "")): str,
                vol.Required(CONF_ENVIRONMENT, default=data.get(CONF_ENVIRONMENT, "prod")): vol.In(["prod"]),
                vol.Required(CONF_VEHICLE_ID, default=data.get(CONF_VEHICLE_ID, "")): str,
            })
        )

    async def async_step_options(self, user_input=None):
        """Options flow: change polling interval (and add more options here)."""
        entry = self._async_current_entries()[0] if self._async_current_entries() else None
        options = entry.options if entry else {}
        current_interval = options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema({
                vol.Required(CONF_UPDATE_INTERVAL, default=current_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=60)
                ),
            })
        )
