"""The Visual Switch Manager integration for Home Assistant."""
import logging
from pathlib import Path
from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "visual_switch_manager"
PANEL_URL_PATH = "visual_switch_manager"
STATIC_URL_PATH = "/visual_switch_manager_static"
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Visual Switch Manager component via YAML (if any, but we prefer UI)."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Visual Switch Manager from a config entry."""
    _LOGGER.info("Setting up Visual Switch Manager integration")
    hass.data.setdefault(DOMAIN, {})

    # Register static path for frontend assets
    frontend_dir = Path(__file__).parent / "frontend"
    if hasattr(hass.http, "async_register_static_paths"):
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                url_path=STATIC_URL_PATH,
                path=str(frontend_dir),
                cache_headers=False,
            )
        ])
    else:
        hass.http.register_static_path(
            STATIC_URL_PATH,
            str(frontend_dir),
            cache_headers=False,
        )

    # Register sidebar panel pointing to our static index.html
    frontend.async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title="Switch Manager",
        sidebar_icon="mdi:toggle-switch-variant",
        frontend_url_path=PANEL_URL_PATH,
        config={"url": f"{STATIC_URL_PATH}/index.html"},
        require_admin=False,
    )

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

    # If no more entries remain, remove sidebar panel and domain key
    if not hass.data.get(DOMAIN):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        hass.data.pop(DOMAIN, None)

    return True