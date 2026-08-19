"""Config flow for Visual Switch Manager integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import logging

DOMAIN = "visual_switch_manager"
_LOGGER = logging.getLogger(__name__)

class VisualSwitchManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Visual Switch Manager."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user configures the integration via UI."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id("visual_switch_manager_instance")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title="Visual Switch Manager", data=user_input)

        data_schema = vol.Schema({
            vol.Optional("enable_advanced_logging", default=False): bool,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return VisualSwitchManagerOptionsFlow(config_entry)

class VisualSwitchManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Visual Switch Manager."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Optional(
                "default_transition_time", 
                default=self.config_entry.options.get("default_transition_time", 1.0)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
        })

        return self.async_show_form(step_id="init", data_schema=options_schema)