"""The Visual Switch Manager integration for Home Assistant."""
import logging
from pathlib import Path
from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

DOMAIN = "visual_switch_manager"
PANEL_URL_PATH = "visual_switch_manager"
STATIC_URL_PATH = "/visual_switch_manager_static"
STORAGE_KEY = "visual_switch_manager_mappings"
STORAGE_VERSION = 1
_LOGGER = logging.getLogger(__name__)

class VisualSwitchManagerMappingsView(HomeAssistantView):
    url = "/api/visual_switch_manager/mappings"
    name = "api:visual_switch_manager:mappings"
    requires_auth = True

    def __init__(self, store: Store) -> None:
        self.store = store

    async def get(self, request):
        """Get all saved mappings."""
        data = await self.store.async_load() or {}
        return self.json(data)

    async def post(self, request):
        """Save mappings."""
        data = await request.json()
        await self.store.async_save(data)
        return self.json({"status": "ok", "saved": data})

class VisualSwitchManagerEntitiesView(HomeAssistantView):
    url = "/api/visual_switch_manager/entities"
    name = "api:visual_switch_manager:entities"
    requires_auth = True

    async def get(self, request):
        """Get all controllable entities from Home Assistant."""
        hass: HomeAssistant = request.app["hass"]
        states = hass.states.async_all()
        allowed_domains = {"light", "scene", "media_player", "automation", "script", "switch", "fan", "climate", "cover"}
        entities = [
            {
                "entity_id": state.entity_id,
                "name": state.attributes.get("friendly_name", state.entity_id),
                "domain": state.domain,
                "state": state.state
            }
            for state in states
            if state.domain in allowed_domains
        ]
        return self.json(entities)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Visual Switch Manager component via YAML (if any, but we prefer UI)."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Visual Switch Manager from a config entry."""
    _LOGGER.info("Setting up Visual Switch Manager integration")
    hass.data.setdefault(DOMAIN, {})

    # Register persistent storage and HTTP API views
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    hass.data[DOMAIN]["store"] = store
    hass.http.register_view(VisualSwitchManagerMappingsView(store))
    hass.http.register_view(VisualSwitchManagerEntitiesView())

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
        
    async def handle_z2m_event(event):
        """Handle events from Zigbee2MQTT via MQTT."""
        _LOGGER.debug(f"Received Z2M event: {event.data}")

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