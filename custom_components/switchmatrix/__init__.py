"""SwitchMatrix: Universal Switch Automation Builder for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant import config_entries
from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType

from .automation_builder import AutomationBuilder
from .const import (
    DOMAIN,
    NAME,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
    STATIC_URL_PATH,
)
from .websocket import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up SwitchMatrix component."""
    hass.data.setdefault(DOMAIN, {})

    # Register WebSocket commands
    async_register_websocket_commands(hass)

    # Register static frontend path
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

    # Register sidebar panel
    frontend.async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config={"url": f"{STATIC_URL_PATH}/index.html"},
        require_admin=False,
    )

    # Automatically ensure config entry exists
    if not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
            )
        )

    _LOGGER.info("SwitchMatrix v1.0 successfully initialized")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SwitchMatrix from a config entry."""
    _LOGGER.info("Setting up SwitchMatrix entry: %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "builder": AutomationBuilder(hass),
    }
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
    return True
