# custom_components/evlinkha/config_flow.py

from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN, CONF_API_KEY, CONF_ENVIRONMENT, CONF_VEHICLE_ID, CONF_UPDATE_INTERVAL

DEFAULT_UPDATE_INTERVAL = 6  # minutes

class EvlinkhaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EVLinkHA."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Här kan du lägga in logik för att testa API-nyckeln, fordonet etc innan du accepterar
            return self.async_create_entry(title="EVLinkHA", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_ENVIRONMENT, default="prod"): vol.In(["prod"]),
                vol.Required(CONF_VEHICLE_ID): str,
            }),
            errors=errors,
        )

    async def async_step_options(self, user_input=None):
        """Handle options flow."""
        # Hämta befintliga inställningar om de finns
        if self._async_current_entries():
            entry = self._async_current_entries()[0]
            current_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        else:
            current_interval = DEFAULT_UPDATE_INTERVAL

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
