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

async def async_execute_mapping_action(hass: HomeAssistant, action_data: dict):
    """Execute a mapped service call in Home Assistant."""
    try:
        service_str = action_data.get("service")  # e.g., "light.toggle"
        entity_id = action_data.get("entity")    # e.g., "light.vardagsrum_tak"

        if not service_str:
            return

        parts = service_str.split(".", 1)
        if len(parts) != 2:
            return

        domain, service = parts[0], parts[1]
        service_data = {}
        if entity_id:
            service_data["entity_id"] = entity_id

        _LOGGER.info("Executing Visual Switch Manager action: %s.%s on %s", domain, service, entity_id)
        await hass.services.async_call(
            domain=domain,
            service=service,
            service_data=service_data,
            blocking=False,
        )
    except Exception as err:
        _LOGGER.exception("Failed to execute mapped action: %s", err)

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

from homeassistant.helpers import device_registry as dr, storage as storage_helper

class VisualSwitchManagerDevicesView(HomeAssistantView):
    url = "/api/visual_switch_manager/devices"
    name = "api:visual_switch_manager:devices"
    requires_auth = True

    async def get(self, request):
        """Get all paired physical devices from Home Assistant device registry."""
        hass: HomeAssistant = request.app["hass"]
        dev_reg = dr.async_get(hass)
        
        devices = []
        for dev in dev_reg.devices.values():
            devices.append({
                "id": dev.id,
                "name": dev.name_by_user or dev.name or f"{dev.manufacturer or ''} {dev.model or ''}".strip(),
                "manufacturer": dev.manufacturer or "Generic",
                "model": dev.model or "Remote / Switch",
                "area_id": dev.area_id,
                "identifiers": [list(i) for i in dev.identifiers],
            })
        
        return self.json(devices)

class VisualSwitchManagerTestActionView(HomeAssistantView):
    url = "/api/visual_switch_manager/test_action"
    name = "api:visual_switch_manager:test_action"
    requires_auth = True

    async def post(self, request):
        """Execute a service action immediately for live testing."""
        hass: HomeAssistant = request.app["hass"]
        data = await request.json()
        await async_execute_mapping_action(hass, data)
        return self.json({"status": "executed", "action": data})

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
    hass.http.register_view(VisualSwitchManagerDevicesView())
    hass.http.register_view(VisualSwitchManagerTestActionView())

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

    # Store entry-specific data and resources
    hass.data[DOMAIN][entry.entry_id] = {
        "data": entry.data,
        "unsubscribers": [],
    }

    async def handle_physical_event(event_type: str, event_data: dict):
        """Process incoming physical switch event and execute matching Home Assistant action."""
        _LOGGER.debug("Received %s event: %s", event_type, event_data)
        saved_data = await store.async_load() or {}
        if not saved_data:
            return

        # Execute mapped actions for configured switches
        for dev_id, dev_mappings in saved_data.items():
            for target_id, action_info in dev_mappings.items():
                if action_info and isinstance(action_info, dict):
                    await async_execute_mapping_action(hass, action_info)

    # Listeners for ZHA, Zigbee2MQTT, Matter, and deCONZ
    unsub_zha = hass.bus.async_listen("zha_event", lambda e: hass.async_create_task(handle_physical_event("ZHA", e.data)))
    unsub_z2m = hass.bus.async_listen("mqtt_message", lambda e: hass.async_create_task(handle_physical_event("Zigbee2MQTT", e.data)))
    unsub_matter = hass.bus.async_listen("matter_event", lambda e: hass.async_create_task(handle_physical_event("Matter", e.data)))
    unsub_deconz = hass.bus.async_listen("deconz_event", lambda e: hass.async_create_task(handle_physical_event("deCONZ", e.data)))

    hass.data[DOMAIN][entry.entry_id]["unsubscribers"].extend([
        unsub_zha,
        unsub_z2m,
        unsub_matter,
        unsub_deconz,
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