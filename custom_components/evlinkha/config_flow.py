from homeassistant import config_entries
import voluptuous as vol
import logging
from .const import DOMAIN, CONF_API_KEY, CONF_VEHICLE_ID, CONF_UPDATE_INTERVAL
from .api import EVLinkHAClient

DEFAULT_UPDATE_INTERVAL = 6
_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EVLinkHA."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            _LOGGER.debug(f"[ConfigFlow] User entered API key: {api_key}")

            # Validera API-key mot backend!
            try:
                client = EVLinkHAClient(self.hass, api_key, "https://api.evlinkha.se", "dummy")
                _LOGGER.debug("[ConfigFlow] Created EVLinkHAClient for API key validation")
                userinfo = await client.async_get_userinfo()
                _LOGGER.debug(f"[ConfigFlow] Result from async_get_userinfo: {userinfo}")

                if not userinfo:
                    _LOGGER.warning("[ConfigFlow] API key validation failed: No userinfo returned")
                    errors["api_key"] = "invalid_api_key"
                else:
                    _LOGGER.info("[ConfigFlow] API key validated successfully, proceeding to vehicle_id step")
                    # Spara API-key temporärt för nästa steg
                    self.context["api_key"] = api_key
                    return await self.async_step_vehicle()
            except Exception as e:
                _LOGGER.exception(f"[ConfigFlow] Exception during API key validation: {e}")
                errors["base"] = "cannot_connect"

        # Första steget: Endast API-key
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors
        )

    async def async_step_vehicle(self, user_input=None):
        errors = {}
        if user_input is not None:
            vehicle_id = user_input[CONF_VEHICLE_ID]
            api_key = self.context["api_key"]
            _LOGGER.debug(f"[ConfigFlow] User entered vehicle_id: {vehicle_id}")

            # Här kan du (om du vill) validera vehicle_id via API också!
            # Annars skapa entry direkt:
            entry_data = {
                CONF_API_KEY: api_key,
                CONF_VEHICLE_ID: vehicle_id,
            }
            _LOGGER.info("[ConfigFlow] Creating config entry with API key and vehicle_id")
            return self.async_create_entry(title="EVLinkHA", data=entry_data)

        # Andra steget: vehicle_id
        return self.async_show_form(
            step_id="vehicle",
            data_schema=vol.Schema({
                vol.Required(CONF_VEHICLE_ID): str,
            }),
            errors=errors
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._async_current_entries()[0] if self._async_current_entries() else None
        data = entry.data if entry else {}

        if user_input is not None:
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
