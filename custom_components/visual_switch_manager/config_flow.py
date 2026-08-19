"""Config flow for Visual Switch Manager integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaFlowFormStep,
    SchemaOptionsFlowHandler,
)

DOMAIN = "visual_switch_manager"
_LOGGER = logging.getLogger(__name__)

OPTIONS_SCHEMA = vol.Schema({
    vol.Optional("default_transition_time", default=1.0): vol.All(
        vol.Coerce(float), vol.Range(min=0.0)
    ),
})

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(OPTIONS_SCHEMA),
}

class VisualSwitchManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Visual Switch Manager."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user configures the integration via UI."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="Visual Switch Manager", data=user_input)

        data_schema = vol.Schema({
            vol.Optional("enable_advanced_logging", default=False): bool,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return SchemaOptionsFlowHandler(config_entry, OPTIONS_FLOW)