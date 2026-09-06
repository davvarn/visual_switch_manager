"""Device introspection and protocol abstraction engine for SwitchMatrix."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

from .const import (
    ACTION_DOUBLE_PRESS,
    ACTION_LONG_PRESS,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE_CCW,
    ACTION_ROTATE_CW,
    ACTION_TRIPLE_PRESS,
    FORM_BUTTON_2,
    FORM_BUTTON_4,
    FORM_BUTTON_6,
    FORM_DECORA_1GANG,
    FORM_DECORA_2GANG,
    FORM_GENERIC,
    FORM_MICRO_MODULE,
    FORM_ROTARY_DIAL,
    FORM_SCROLL_WHEEL,
    FORM_SMART_PLUG,
    PROTOCOL_ESPHOME,
    PROTOCOL_GENERIC,
    PROTOCOL_MATTER,
    PROTOCOL_SHELLY,
    PROTOCOL_Z2M,
    PROTOCOL_ZHA,
    PROTOCOL_ZWAVE,
)

_LOGGER = logging.getLogger(__name__)

EXCLUDED_VENDORS = {
    "alexxit",
    "google",
    "apple",
    "plex",
    "backup",
    "whisper",
    "piper",
    "openwakeword",
    "android",
    "tapocam",
    "skyconnect",
    "homeassistant",
}


def detect_protocol(dev: dr.DeviceEntry, entities: list[er.RegistryEntry]) -> str:
    """Identify the underlying smart home protocol for a device."""
    ident_domains = [
        ident[0].lower()
        for ident in dev.identifiers
        if isinstance(ident, (list, tuple)) and len(ident) > 0
    ]

    if "zha" in ident_domains:
        return PROTOCOL_ZHA
    if "matter" in ident_domains:
        return PROTOCOL_MATTER
    if "zwave_js" in ident_domains:
        return PROTOCOL_ZWAVE
    if "shelly" in ident_domains:
        return PROTOCOL_SHELLY
    if "esphome" in ident_domains:
        return PROTOCOL_ESPHOME
    if "mqtt" in ident_domains:
        return PROTOCOL_Z2M

    # Check entity platform attributes
    for ent in entities:
        platform = (ent.platform or "").lower()
        if "zha" in platform:
            return PROTOCOL_ZHA
        if "matter" in platform:
            return PROTOCOL_MATTER
        if "zwave_js" in platform:
            return PROTOCOL_ZWAVE
        if "shelly" in platform:
            return PROTOCOL_SHELLY
        if "mqtt" in platform:
            return PROTOCOL_Z2M

    return PROTOCOL_GENERIC


def detect_form_factor(dev: dr.DeviceEntry, model: str, name: str, entities: list[er.RegistryEntry]) -> str:
    """Detect the physical hardware layout / digital twin blueprint form factor."""
    combined = f"{name} {model} {dev.manufacturer or ''}".lower()

    if any(k in combined for k in ["bilresa", "scroll", "wheel"]):
        return FORM_SCROLL_WHEEL
    if any(k in combined for k in ["symfonisk", "dial", "rotary", "knob", "tap dial"]):
        return FORM_ROTARY_DIAL
    if any(k in combined for k in ["opple", "6-button", "6 button", "6gang"]):
        return FORM_BUTTON_6
    if any(k in combined for k in ["styrbar", "4-button", "4 button", "4gang", "tap dial", "ts0044"]):
        return FORM_BUTTON_4
    if any(k in combined for k in ["somrig", "rodret", "tradfri on/off", "2-button", "2 button", "2gang"]):
        return FORM_BUTTON_2
    if any(k in combined for k in ["plug", "socket", "outlet", "smart plug"]):
        return FORM_SMART_PLUG
    if any(k in combined for k in ["relay", "micro", "shelly 1", "shelly plus 1", "sonoff mini"]):
        return FORM_MICRO_MODULE
    if any(k in combined for k in ["2-gang", "double rocker", "dual rocker", "2 gang"]):
        return FORM_DECORA_2GANG
    if any(k in combined for k in ["switch", "wall switch", "rocker", "dimmer", "decora"]):
        return FORM_DECORA_1GANG

    # Fallback based on event count
    event_count = sum(1 for e in entities if e.domain == "event")
    if event_count >= 6:
        return FORM_BUTTON_6
    if event_count >= 4:
        return FORM_BUTTON_4
    if event_count >= 2:
        return FORM_BUTTON_2

    return FORM_DECORA_1GANG


async def async_get_discovered_devices(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Scan Home Assistant device, entity, and area registries for controllable switches/remotes."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    area_reg = ar.async_get(hass)

    # Map device IDs to their entities
    device_to_entities: dict[str, list[er.RegistryEntry]] = {}
    for ent in ent_reg.entities.values():
        if ent.device_id:
            device_to_entities.setdefault(ent.device_id, []).append(ent)

    devices_output: list[dict[str, Any]] = []

    for dev in dev_reg.devices.values():
        name = (dev.name_by_user or dev.name or "").strip()
        manufacturer = (dev.manufacturer or "Generic").strip()
        model = (dev.model or "Controller").strip()
        search_str = f"{name} {manufacturer} {model}".lower()

        # Filter out system devices
        if any(ex in search_str for ex in EXCLUDED_VENDORS):
            continue

        dev_entities = device_to_entities.get(dev.id, [])
        has_event = any(e.domain == "event" for e in dev_entities)
        has_switch = any(e.domain == "switch" for e in dev_entities)
        is_controller_name = any(
            k in search_str
            for k in [
                "remote", "switch", "button", "dial", "wheel", "styrbar", "bilresa",
                "somrig", "rodret", "tradfri", "dimmer", "symfonisk", "opple", "cube",
                "shelly", "sonoff", "hue dimmer", "wall switch", "keypad",
            ]
        )

        if not (has_event or has_switch or is_controller_name):
            continue

        protocol = detect_protocol(dev, dev_entities)
        form_factor = detect_form_factor(dev, model, name, dev_entities)

        area_name = "Unassigned"
        if dev.area_id:
            area_entry = area_reg.async_get_area(dev.area_id)
            if area_entry:
                area_name = area_entry.name

        devices_output.append({
            "id": dev.id,
            "name": name or f"{manufacturer} {model}",
            "manufacturer": manufacturer,
            "model": model,
            "area_id": dev.area_id,
            "area_name": area_name,
            "protocol": protocol,
            "form_factor": form_factor,
            "has_event_entities": has_event,
            "entity_count": len(dev_entities),
            "sw_version": dev.sw_version or "",
        })

    # Sort with prioritized event controllers and alphabetical name
    devices_output.sort(key=lambda d: (not d["has_event_entities"], d["name"].lower()))
    return devices_output


async def async_get_device_capabilities(hass: HomeAssistant, device_id: str) -> dict[str, Any]:
    """Inspect detailed trigger capabilities and interactive zones for a specific device."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    dev = dev_reg.async_get(device_id)

    if not dev:
        return {"error": "Device not found"}

    entities = [e for e in ent_reg.entities.values() if e.device_id == device_id]
    protocol = detect_protocol(dev, entities)
    form_factor = detect_form_factor(
        dev,
        dev.model or "",
        dev.name_by_user or dev.name or "",
        entities,
    )

    # Attempt to query native Home Assistant device automations
    raw_triggers: list[dict[str, Any]] = []
    try:
        from homeassistant.components.device_automation import (
            async_get_device_automations,
        )
        raw_triggers = await async_get_device_automations(hass, "trigger", device_id)
    except Exception as err:
        _LOGGER.debug("Device automation introspect fallback for %s: %s", device_id, err)

    # Extract event entities and map interactive buttons
    interactive_buttons = _build_interactive_button_zones(
        form_factor=form_factor,
        entities=entities,
        raw_triggers=raw_triggers,
        protocol=protocol,
        device_name=dev.name or "",
    )

    return {
        "device_id": device_id,
        "name": dev.name_by_user or dev.name or "Device",
        "manufacturer": dev.manufacturer or "Generic",
        "model": dev.model or "Switch",
        "protocol": protocol,
        "form_factor": form_factor,
        "buttons": interactive_buttons,
        "raw_trigger_count": len(raw_triggers),
        "entities": [
            {
                "entity_id": e.entity_id,
                "domain": e.domain,
                "name": e.name or e.original_name,
                "disabled": e.disabled,
            }
            for e in entities
        ],
    }


def _build_interactive_button_zones(
    form_factor: str,
    entities: list[er.RegistryEntry],
    raw_triggers: list[dict[str, Any]],
    protocol: str,
    device_name: str,
) -> list[dict[str, Any]]:
    """Construct normalized interactive button zones with supported trigger gestures."""
    zones: list[dict[str, Any]] = []
    event_entities = sorted(
        [e.entity_id for e in entities if e.domain == "event"],
        key=lambda x: _natural_sort_key(x),
    )

    # 1. IKEA BILRESA SCROLL WHEEL (3 Channels / Groups)
    if form_factor == FORM_SCROLL_WHEEL:
        for ch in [1, 2, 3]:
            btn_center = 3 if ch == 1 else (6 if ch == 2 else 9)
            btn_cw = 1 if ch == 1 else (4 if ch == 2 else 7)
            btn_ccw = 2 if ch == 1 else (5 if ch == 2 else 8)

            zones.append({
                "zone_id": f"ch{ch}_center",
                "label": f"Channel {ch}: Center Click",
                "channel": ch,
                "icon": "mdi:circle-slice-8",
                "entity_id": _find_entity_by_btn_num(event_entities, btn_center),
                "supported_actions": [ACTION_PRESS, ACTION_DOUBLE_PRESS, ACTION_LONG_PRESS],
                "default_service": "light.toggle",
            })
            zones.append({
                "zone_id": f"ch{ch}_cw",
                "label": f"Channel {ch}: Rotate Clockwise (+)",
                "channel": ch,
                "icon": "mdi:rotate-right",
                "entity_id": _find_entity_by_btn_num(event_entities, btn_cw),
                "supported_actions": [ACTION_ROTATE_CW],
                "default_service": "light.brightness_step_up",
            })
            zones.append({
                "zone_id": f"ch{ch}_ccw",
                "label": f"Channel {ch}: Rotate Counter-Clockwise (-)",
                "channel": ch,
                "icon": "mdi:rotate-left",
                "entity_id": _find_entity_by_btn_num(event_entities, btn_ccw),
                "supported_actions": [ACTION_ROTATE_CCW],
                "default_service": "light.brightness_step_down",
            })
        return zones

    # 2. ROTARY DIAL / SYMFONISK / HUE TAP DIAL
    if form_factor == FORM_ROTARY_DIAL:
        zones.append({
            "zone_id": "dial_center",
            "label": "Dial Press / Click",
            "icon": "mdi:knob",
            "entity_id": event_entities[0] if event_entities else None,
            "supported_actions": [ACTION_PRESS, ACTION_DOUBLE_PRESS, ACTION_LONG_PRESS],
            "default_service": "media_player.media_play_pause",
        })
        zones.append({
            "zone_id": "dial_cw",
            "label": "Rotate Clockwise (+)",
            "icon": "mdi:rotate-right",
            "supported_actions": [ACTION_ROTATE_CW],
            "default_service": "media_player.volume_up",
        })
        zones.append({
            "zone_id": "dial_ccw",
            "label": "Rotate Counter-Clockwise (-)",
            "icon": "mdi:rotate-left",
            "supported_actions": [ACTION_ROTATE_CCW],
            "default_service": "media_player.volume_down",
        })
        return zones

    # 3. 4-BUTTON SCENE CONTROLLER (IKEA Styrbar, Hue Dimmer, etc.)
    if form_factor == FORM_BUTTON_4:
        labels = [
            ("btn_top", "Top Button (▲ On / Dim Up)", "mdi:arrow-up-bold", "light.turn_on"),
            ("btn_bottom", "Bottom Button (▼ Off / Dim Down)", "mdi:arrow-down-bold", "light.turn_off"),
            ("btn_left", "Left Button (◀ Previous Scene)", "mdi:arrow-left-bold", "scene.turn_on"),
            ("btn_right", "Right Button (▶ Next Scene)", "mdi:arrow-right-bold", "scene.turn_on"),
        ]
        for idx, (zid, lbl, icon, def_svc) in enumerate(labels):
            ent = event_entities[idx] if idx < len(event_entities) else None
            zones.append({
                "zone_id": zid,
                "label": lbl,
                "icon": icon,
                "entity_id": ent,
                "supported_actions": [ACTION_PRESS, ACTION_DOUBLE_PRESS, ACTION_LONG_PRESS, ACTION_RELEASE],
                "default_service": def_svc,
            })
        return zones

    # 4. 2-BUTTON / ROCKER / SOMRIG / RODRET
    if form_factor == FORM_BUTTON_2:
        labels = [
            ("top_button", "Top Rocker / Button 1", "mdi:toggle-switch", "light.turn_on"),
            ("bottom_button", "Bottom Rocker / Button 2", "mdi:toggle-switch-off", "light.turn_off"),
        ]
        for idx, (zid, lbl, icon, def_svc) in enumerate(labels):
            ent = event_entities[idx] if idx < len(event_entities) else None
            zones.append({
                "zone_id": zid,
                "label": lbl,
                "icon": icon,
                "entity_id": ent,
                "supported_actions": [ACTION_PRESS, ACTION_DOUBLE_PRESS, ACTION_LONG_PRESS, ACTION_RELEASE],
                "default_service": def_svc,
            })
        return zones

    # 5. 6-BUTTON SCENE CONTROLLER (Aqara Opple 6-gang)
    if form_factor == FORM_BUTTON_6:
        for idx in range(6):
            ent = event_entities[idx] if idx < len(event_entities) else None
            zones.append({
                "zone_id": f"button_{idx + 1}",
                "label": f"Button {idx + 1}",
                "icon": f"mdi:numeric-{idx + 1}-box",
                "entity_id": ent,
                "supported_actions": [ACTION_PRESS, ACTION_DOUBLE_PRESS, ACTION_LONG_PRESS],
                "default_service": "light.toggle" if idx < 2 else ("light.brightness_step_up" if idx < 4 else "scene.turn_on"),
            })
        return zones

    # 6. STANDARD 1-GANG DECORA ROCKER (Default)
    zones.append({
        "zone_id": "rocker_top",
        "label": "Top Paddle (Turn On / Dim Up)",
        "icon": "mdi:arrow-up",
        "entity_id": event_entities[0] if event_entities else None,
        "supported_actions": [ACTION_PRESS, ACTION_DOUBLE_PRESS, ACTION_TRIPLE_PRESS, ACTION_LONG_PRESS],
        "default_service": "light.turn_on",
    })
    zones.append({
        "zone_id": "rocker_bottom",
        "label": "Bottom Paddle (Turn Off / Dim Down)",
        "icon": "mdi:arrow-down",
        "entity_id": event_entities[1] if len(event_entities) > 1 else None,
        "supported_actions": [ACTION_PRESS, ACTION_DOUBLE_PRESS, ACTION_TRIPLE_PRESS, ACTION_LONG_PRESS],
        "default_service": "light.turn_off",
    })
    return zones


def _find_entity_by_btn_num(entities: list[str], btn_num: int) -> str | None:
    """Find specific event entity ending with or containing button index."""
    target_suffix = f"_{btn_num}"
    target_pattern = f"button_{btn_num}"
    for e in entities:
        e_lower = e.lower()
        if e_lower.endswith(target_suffix) or target_pattern in e_lower:
            return e
    # If 9 event entities exist, index into them directly
    if len(entities) >= 9 and 1 <= btn_num <= len(entities):
        return entities[btn_num - 1]
    return None


def _natural_sort_key(s: str) -> list[int | str]:
    """Helper for natural sorting of entity numbers."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]
