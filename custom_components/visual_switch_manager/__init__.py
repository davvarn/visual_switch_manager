"""The Visual Switch Manager integration for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "visual_switch_manager"
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Visual Switch Manager component via YAML (if any, but we prefer UI)."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Visual Switch Manager from a config entry."""
    _LOGGER.info("Setting up Visual Switch Manager integration")
    hass.data.setdefault(DOMAIN, {})

    # Store entry-specific data and resources (like unsubscribe callbacks)
    hass.data[DOMAIN][entry.entry_id] = {
        "data": entry.data,
        "unsubscribers": [],
    }

    async def handle_zha_event(event):
        """Handle events from ZHA (Zigbee Home Automation)."""
        _LOGGER.debug(f"Received ZHA event: {event.data}")
        # Routing logic goes here
        
    async def handle_z2m_event(event):
        """Handle events from Zigbee2MQTT via MQTT."""
        _LOGGER.debug(f"Received Z2M event: {event.data}")
        # Routing logic goes here

    # Register listeners and keep the unsubscribe callables so we can clean up.
    unsub_zha = hass.bus.async_listen("zha_event", handle_zha_event)
    unsub_z2m = hass.bus.async_listen("mqtt_message", handle_z2m_event)

    hass.data[DOMAIN][entry.entry_id]["unsubscribers"].extend([
        unsub_zha,
        unsub_z2m,
    ])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Visual Switch Manager integration")
    domain_data = hass.data.get(DOMAIN, {})

    entry_store = domain_data.pop(entry.entry_id, None)
    if entry_store:
        for unsub in entry_store.get("unsubscribers", []):
            try:
                unsub()
            except Exception:  # pragma: no cover - defensive
                _LOGGER.exception("Error while unsubscribing listener for %s", entry.entry_id)

    # If no more entries remain, remove the domain key entirely.
    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)

    return True