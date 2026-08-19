"""The Visual Switch Manager integration for Home Assistant."""
import logging
from pathlib import Path
from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
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

        # Handle brightness step up/down for lights
        if domain == "light":
            if service in ("brightness_step_up", "brightness_up"):
                service = "turn_on"
                service_data["brightness_step_pct"] = 10
            elif service in ("brightness_step_down", "brightness_down"):
                service = "turn_on"
                service_data["brightness_step_pct"] = -10

        _LOGGER.info("Executing Visual Switch Manager action: %s.%s on %s (data: %s)", domain, service, entity_id, service_data)
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
        """Get controllable target entities from Home Assistant, filtered for useful automation targets."""
        hass: HomeAssistant = request.app["hass"]
        states = hass.states.async_all()
        allowed_domains = {"light", "scene", "media_player", "automation", "script", "switch", "cover", "climate", "fan", "lock"}
        
        entities = []
        for state in states:
            if state.domain not in allowed_domains:
                continue
            # Skip browser_mod and hidden entities
            if state.entity_id.startswith(("light.browser_", "media_player.browser_")):
                continue
            
            entities.append({
                "entity_id": state.entity_id,
                "name": state.attributes.get("friendly_name", state.entity_id),
                "domain": state.domain,
                "state": state.state
            })

        entities.sort(key=lambda e: (e["domain"], e["name"]))
        return self.json(entities)

class VisualSwitchManagerDevicesView(HomeAssistantView):
    url = "/api/visual_switch_manager/devices"
    name = "api:visual_switch_manager:devices"
    requires_auth = True

    async def get(self, request):
        """Get paired physical switch/remote devices from Home Assistant device registry, filtering out non-remote system devices."""
        hass: HomeAssistant = request.app["hass"]
        dev_reg = dr.async_get(hass)
        ent_reg = er.async_get(hass)

        # Excluded software/system manufacturers and names
        excluded_keywords = [
            "alexxit", "whisper", "google ai", "plex", "backup", "android tv", 
            "tapocam", "camera", "skyconnect", "nabu casa", "home assistant",
            "tts", "stt", "ai agent", "forecast", "speedtest", "hacs", "updater"
        ]

        # Allowed integration domains for remotes
        remote_domains = {"matter", "zha", "mqtt", "deconz", "hue", "bthome", "shelly", "esphome", "lutron_caseta", "tasmota"}

        # Find all device IDs that have event entities or battery or switch entities
        dev_entities = {}
        for ent in ent_reg.entities.values():
            if ent.device_id:
                dev_entities.setdefault(ent.device_id, []).append(ent.domain)

        devices = []
        for dev in dev_reg.devices.values():
            name = (dev.name_by_user or dev.name or "").strip()
            manufacturer = (dev.manufacturer or "").strip()
            model = (dev.model or "").strip()
            full_str = f"{name} {manufacturer} {model}".lower()

            # Skip excluded system integrations
            if any(kw in full_str for kw in excluded_keywords):
                continue

            # Check if device has event entities or is from a remote domain or has remote/switch in name/model
            has_events = "event" in dev_entities.get(dev.id, [])
            is_remote_domain = any(ident[0] in remote_domains for ident in dev.identifiers if isinstance(ident, (list, tuple)) and len(ident) > 0)
            is_remote_named = any(k in full_str for k in ["remote", "switch", "button", "dial", "wheel", "styrbar", "bilresa", "somrig", "rodret", "tradfri", "dimmer", "symfonisk", "opple", "cube", "smart plug", "inspelning"])

            if has_events or is_remote_domain or is_remote_named:
                devices.append({
                    "id": dev.id,
                    "name": name or f"{manufacturer} {model}".strip() or "Unnamed Remote",
                    "manufacturer": manufacturer or "Generic",
                    "model": model or "Remote / Switch",
                    "area_id": dev.area_id,
                    "has_events": has_events,
                    "identifiers": [list(i) for i in dev.identifiers],
                })

        # Sort so devices with event entities or remotes appear first
        devices.sort(key=lambda d: (not d.get("has_events"), d["name"]))
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
    """Set up the Visual Switch Manager component via YAML or auto-discovery."""
    hass.data.setdefault(DOMAIN, {})
    # Automatically ensure a config entry exists so async_setup_entry is executed
    if not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
            )
        )
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Visual Switch Manager from a config entry."""
    _LOGGER.warning("Visual Switch Manager: Setting up integration entry %s", entry.entry_id)
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

    async def async_process_state_changed(entity_id: str, new_state):
        """Process state change on event entity."""
        saved_data = await store.async_load() or {}
        if not saved_data:
            _LOGGER.debug("Visual Switch Manager: No saved mappings configured")
            return

        ent_reg = er.async_get(hass)
        ent_entry = ent_reg.async_get(entity_id)
        device_id = ent_entry.device_id if ent_entry else None
        ent_lower = entity_id.lower()

        # Robust button number extraction (handles _button_3, _knapp_3, _3, button_3)
        btn_num = None
        m = re.search(r'(?:button|knapp|switch|input|btn)?_?([1-9])$', ent_lower)
        if m:
            btn_num = int(m.group(1))
        else:
            m = re.search(r'button_([1-9])\b', ent_lower)
            if m:
                btn_num = int(m.group(1))

        _LOGGER.warning("Visual Switch Manager: Processing entity %s (device %s, btn_num=%s)", entity_id, device_id, btn_num)

        for blueprint_id, dev_data in saved_data.items():
            if not isinstance(dev_data, dict):
                continue

            assigned_id = dev_data.get("assigned_device_id")
            
            # Match check: assigned_id match, device_id match, or fallback
            is_match = False
            if assigned_id and device_id and assigned_id == device_id:
                is_match = True
            elif not assigned_id or blueprint_id == device_id:
                is_match = True
            elif assigned_id and ent_reg:
                device_entries = er.async_entries_for_device(ent_reg, assigned_id)
                if any(e.entity_id == entity_id for e in device_entries):
                    is_match = True
            elif blueprint_id == "bilresa_wheel" and btn_num is not None:
                # If BILRESA is configured in plugin, match button event
                is_match = True

            if not is_match:
                continue

            mappings = dev_data.get("mappings", dev_data)

            target_key = None
            if blueprint_id == "bilresa_wheel":
                # Channel 1: 3=Center Press, 1=Rotate Right (CW), 2=Rotate Left (CCW)
                if btn_num == 3: target_key = "g1_wheel_center"
                elif btn_num == 1: target_key = "g1_wheel_cw"
                elif btn_num == 2: target_key = "g1_wheel_ccw"
                # Channel 2: 6=Center Press, 4=Rotate Right (CW), 5=Rotate Left (CCW)
                elif btn_num == 6: target_key = "g2_wheel_center"
                elif btn_num == 4: target_key = "g2_wheel_cw"
                elif btn_num == 5: target_key = "g2_wheel_ccw"
                # Channel 3: 9=Center Press, 7=Rotate Right (CW), 8=Rotate Left (CCW)
                elif btn_num == 9: target_key = "g3_wheel_center"
                elif btn_num == 7: target_key = "g3_wheel_cw"
                elif btn_num == 8: target_key = "g3_wheel_ccw"

                if not target_key or target_key not in mappings:
                    if btn_num in (1, 3, 6, 9): target_key = "wheel_center"
                    elif btn_num in (1, 4, 7): target_key = "wheel_cw"
                    elif btn_num in (2, 5, 8): target_key = "wheel_ccw"

            elif blueprint_id == "bilresa_2btn":
                if btn_num == 1: target_key = "top_button"
                elif btn_num == 2: target_key = "bottom_button"
            elif blueprint_id == "styrbar":
                if btn_num == 1: target_key = "on"
                elif btn_num == 2: target_key = "off"
                elif btn_num == 3: target_key = "left"
                elif btn_num == 4: target_key = "right"
            elif blueprint_id == "somrig":
                if btn_num == 1: target_key = "btn1"
                elif btn_num == 2: target_key = "btn2"
            elif blueprint_id == "rodret":
                if btn_num == 1: target_key = "plus"
                elif btn_num == 2: target_key = "minus"
            elif blueprint_id in ("hue_dimmer_v1", "hue_dimmer_v2"):
                if btn_num == 1: target_key = "hue_on" if blueprint_id == "hue_dimmer_v2" else "on"
                elif btn_num == 2: target_key = "hue_up" if blueprint_id == "hue_dimmer_v2" else "up"
                elif btn_num == 3: target_key = "hue_down" if blueprint_id == "hue_dimmer_v2" else "down"
                elif btn_num == 4: target_key = "hue_off" if blueprint_id == "hue_dimmer_v2" else "off"

            if target_key and target_key in mappings:
                action_info = mappings[target_key]
                if action_info and isinstance(action_info, dict) and "service" in action_info:
                    _LOGGER.warning("Visual Switch Manager: Executing mapped action for %s: %s", target_key, action_info)
                    await async_execute_mapping_action(hass, action_info)
                    return

            # Check if group lamp was assigned directly for that group (e.g. group_1_entity)
            if blueprint_id == "bilresa_wheel":
                g_idx = 1 if btn_num in (1, 2, 3) else (2 if btn_num in (4, 5, 6) else (3 if btn_num in (7, 8, 9) else None))
                if g_idx:
                    group_entity = dev_data.get(f"group_{g_idx}_entity")
                    if group_entity:
                        if btn_num in (3, 6, 9):
                            await async_execute_mapping_action(hass, {"service": "light.toggle", "entity": group_entity})
                            return
                        elif btn_num in (1, 4, 7):
                            await async_execute_mapping_action(hass, {"service": "light.brightness_step_up", "entity": group_entity})
                            return
                        elif btn_num in (2, 5, 8):
                            await async_execute_mapping_action(hass, {"service": "light.brightness_step_down", "entity": group_entity})
                            return

            # Check direct key match or button number in mapping
            for k, action_info in mappings.items():
                if k in ent_lower and isinstance(action_info, dict):
                    await async_execute_mapping_action(hass, action_info)
                    return

            # If only 1 mapping configured on this remote, execute it!
            if len(mappings) == 1:
                single_action = list(mappings.values())[0]
                if isinstance(single_action, dict) and "service" in single_action:
                    await async_execute_mapping_action(hass, single_action)

    @callback
    def handle_state_changed(event):
        """Synchronously capture state changes of event entities and dispatch."""
        entity_id = event.data.get("entity_id", "")
        if not entity_id.startswith("event.") and not entity_id.startswith("sensor."):
            return

        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in ("unavailable", "unknown"):
            return

        event_type_attr = new_state.attributes.get("event_type", "press") if new_state.attributes else "press"
        _LOGGER.warning("Visual Switch Manager: RAW EVENT DETECTED on %s (state=%s, event_type=%s)", entity_id, new_state.state, event_type_attr)
        hass.async_create_task(async_process_state_changed(entity_id, new_state))

    async def handle_physical_event(event_type: str, event_data: dict):
        """Process incoming physical switch event from ZHA, Z2M, Matter, deCONZ."""
        _LOGGER.warning("Received %s event: %s", event_type, event_data)
        saved_data = await store.async_load() or {}
        if not saved_data:
            return

        incoming_dev_id = event_data.get("device_id") or event_data.get("ieee")

        for blueprint_id, dev_data in saved_data.items():
            if not isinstance(dev_data, dict):
                continue
            assigned_id = dev_data.get("assigned_device_id")
            if assigned_id and incoming_dev_id and assigned_id != incoming_dev_id:
                continue

            mappings = dev_data.get("mappings", dev_data)
            for target_id, action_info in mappings.items():
                if action_info and isinstance(action_info, dict) and "service" in action_info:
                    await async_execute_mapping_action(hass, action_info)

    @callback
    def handle_physical_event_cb(event_type: str, event_data: dict):
        hass.async_create_task(handle_physical_event(event_type, event_data))

    # Event listeners
    unsub_state = hass.bus.async_listen(EVENT_STATE_CHANGED, handle_state_changed)
    unsub_zha = hass.bus.async_listen("zha_event", lambda e: handle_physical_event_cb("ZHA", e.data))
    unsub_z2m = hass.bus.async_listen("mqtt_message", lambda e: handle_physical_event_cb("Zigbee2MQTT", e.data))
    unsub_matter = hass.bus.async_listen("matter_event", lambda e: handle_physical_event_cb("Matter", e.data))
    unsub_deconz = hass.bus.async_listen("deconz_event", lambda e: handle_physical_event_cb("deCONZ", e.data))

    hass.data[DOMAIN][entry.entry_id]["unsubscribers"].extend([
        unsub_state,
        unsub_zha,
        unsub_z2m,
        unsub_matter,
        unsub_deconz,
    ])
    _LOGGER.warning("Visual Switch Manager: Event listeners successfully registered and ACTIVE!")

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
            except Exception:
                _LOGGER.exception("Error while unsubscribing listener for %s", entry.entry_id)

    # If no more entries remain, remove sidebar panel and domain key
    if not hass.data.get(DOMAIN):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        hass.data.pop(DOMAIN, None)

    return True