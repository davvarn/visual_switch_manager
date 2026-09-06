"""WebSocket API handlers for SwitchMatrix."""
from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .automation_builder import AutomationBuilder
from .const import (
    WS_DELETE_AUTOMATION,
    WS_GET_AUTOMATIONS,
    WS_GET_DEVICE_CAPABILITIES,
    WS_GET_DEVICES,
    WS_SAVE_AUTOMATION,
    WS_TEST_ACTION,
)
from .device_introspector import (
    async_get_device_capabilities,
    async_get_discovered_devices,
)

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register SwitchMatrix WebSocket commands."""
    websocket_api.async_register_command(hass, ws_get_devices)
    websocket_api.async_register_command(hass, ws_get_device_capabilities)
    websocket_api.async_register_command(hass, ws_save_automation)
    websocket_api.async_register_command(hass, ws_delete_automation)
    websocket_api.async_register_command(hass, ws_get_automations)
    websocket_api.async_register_command(hass, ws_test_action)
    _LOGGER.debug("SwitchMatrix: WebSocket commands registered successfully")


@websocket_api.websocket_command({
    vol.Required("type"): WS_GET_DEVICES,
})
@websocket_api.async_response
async def ws_get_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle switchmatrix/get_devices command."""
    devices = await async_get_discovered_devices(hass)
    connection.send_result(msg["id"], devices)


@websocket_api.websocket_command({
    vol.Required("type"): WS_GET_DEVICE_CAPABILITIES,
    vol.Required("device_id"): str,
})
@websocket_api.async_response
async def ws_get_device_capabilities(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle switchmatrix/get_capabilities command."""
    device_id = msg["device_id"]
    capabilities = await async_get_device_capabilities(hass, device_id)
    connection.send_result(msg["id"], capabilities)


@websocket_api.websocket_command({
    vol.Required("type"): WS_SAVE_AUTOMATION,
    vol.Required("flow_data"): dict,
})
@websocket_api.async_response
async def ws_save_automation(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle switchmatrix/save_automation command."""
    flow_data = msg["flow_data"]
    builder = AutomationBuilder(hass)

    automation_dict = builder.build_automation(flow_data)
    yaml_code = builder.to_yaml(automation_dict)

    success = await builder.async_save_automation(automation_dict)
    connection.send_result(
        msg["id"],
        {
            "success": success,
            "automation": automation_dict,
            "yaml": yaml_code,
        },
    )


@websocket_api.websocket_command({
    vol.Required("type"): WS_DELETE_AUTOMATION,
    vol.Required("automation_id"): str,
})
@websocket_api.async_response
async def ws_delete_automation(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle switchmatrix/delete_automation command."""
    auto_id = msg["automation_id"]
    builder = AutomationBuilder(hass)
    success = await builder.async_delete_automation(auto_id)
    connection.send_result(msg["id"], {"success": success, "id": auto_id})


@websocket_api.websocket_command({
    vol.Required("type"): WS_GET_AUTOMATIONS,
})
@websocket_api.async_response
async def ws_get_automations(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle switchmatrix/get_automations command."""
    builder = AutomationBuilder(hass)
    automations = await builder.async_get_saved_automations()
    connection.send_result(msg["id"], automations)


@websocket_api.websocket_command({
    vol.Required("type"): WS_TEST_ACTION,
    vol.Required("service"): str,
    vol.Optional("entity_id"): str,
    vol.Optional("data"): dict,
})
@websocket_api.async_response
async def ws_test_action(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle switchmatrix/test_action command for live interactive verification."""
    service_str = msg["service"]
    entity_id = msg.get("entity_id")
    extra_data = msg.get("data", {})

    parts = service_str.split(".", 1)
    if len(parts) != 2:
        connection.send_error(msg["id"], "invalid_service", f"Invalid service string: {service_str}")
        return

    domain, service = parts[0], parts[1]
    service_data = dict(extra_data)

    if entity_id:
        service_data["entity_id"] = entity_id

    # Smart step dimming handling
    if domain == "light":
        if service in ("brightness_step_up", "brightness_up"):
            service = "turn_on"
            service_data["brightness_step_pct"] = 10
        elif service in ("brightness_step_down", "brightness_down"):
            service = "turn_on"
            service_data["brightness_step_pct"] = -10

    try:
        await hass.services.async_call(
            domain=domain,
            service=service,
            service_data=service_data,
            blocking=False,
        )
        connection.send_result(
            msg["id"],
            {"success": True, "domain": domain, "service": service, "data": service_data},
        )
    except Exception as err:
        connection.send_error(msg["id"], "service_call_failed", str(err))
