# custom_components/evlinkha/config_flow.py

from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN, CONF_API_KEY, CONF_ENVIRONMENT, CONF_VEHICLE_ID

class EvlinkhaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="EVLinkHA", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_ENVIRONMENT, default="prod"): vol.In(["prod", "sandbox"]),
                vol.Required(CONF_VEHICLE_ID): str,
            }),
            errors=errors,
        )
