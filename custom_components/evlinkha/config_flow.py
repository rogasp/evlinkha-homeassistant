from homeassistant import config_entries
import voluptuous as vol
from .const import (
    DOMAIN, CONF_API_KEY, CONF_VEHICLE_ID, CONF_UPDATE_INTERVAL
)

DEFAULT_UPDATE_INTERVAL = 6

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_API_KEY): str,
    vol.Required(CONF_VEHICLE_ID): str,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EVLinkHA."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="EVLinkHA", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._async_current_entries()[0] if self._async_current_entries() else None
        data = entry.data if entry else {}

        if user_input is not None:
            # Save new config data
            return self.async_create_entry(title="EVLinkHA", data=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY, default=data.get(CONF_API_KEY, "")): str,
                vol.Required(CONF_VEHICLE_ID, default=data.get(CONF_VEHICLE_ID, "")): str,
            }),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return EVLinkHAOptionsFlowHandler(config_entry)

class EVLinkHAOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for EVLinkHA."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60))
            }),
        )
