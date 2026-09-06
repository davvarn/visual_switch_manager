"""Constants for the SwitchMatrix integration."""

DOMAIN = "switchmatrix"
NAME = "SwitchMatrix"
VERSION = "1.0.0"

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = "switchmatrix_automations"

# Panel & HTTP URLs
PANEL_URL_PATH = "switchmatrix"
PANEL_TITLE = "SwitchMatrix"
PANEL_ICON = "mdi:matrix"
STATIC_URL_PATH = "/switchmatrix_static"

# Protocols
PROTOCOL_ZHA = "zha"
PROTOCOL_Z2M = "zigbee2mqtt"
PROTOCOL_MATTER = "matter"
PROTOCOL_ZWAVE = "zwave_js"
PROTOCOL_SHELLY = "shelly"
PROTOCOL_ESPHOME = "esphome"
PROTOCOL_GENERIC = "generic"

# Physical Form Factors
FORM_DECORA_1GANG = "decora_1gang"
FORM_DECORA_2GANG = "decora_2gang"
FORM_BUTTON_2 = "button_2"
FORM_BUTTON_4 = "button_4"
FORM_BUTTON_6 = "button_6"
FORM_ROTARY_DIAL = "rotary_dial"
FORM_SCROLL_WHEEL = "scroll_wheel"
FORM_MICRO_MODULE = "micro_module"
FORM_SMART_PLUG = "smart_plug"
FORM_GENERIC = "generic"

# Standard Normalized Actions
ACTION_PRESS = "single_press"
ACTION_DOUBLE_PRESS = "double_press"
ACTION_TRIPLE_PRESS = "triple_press"
ACTION_LONG_PRESS = "long_press"
ACTION_RELEASE = "release"
ACTION_ROTATE_CW = "rotate_cw"
ACTION_ROTATE_CCW = "rotate_ccw"

# WebSocket Command Types
WS_GET_DEVICES = "switchmatrix/get_devices"
WS_GET_DEVICE_CAPABILITIES = "switchmatrix/get_capabilities"
WS_SAVE_AUTOMATION = "switchmatrix/save_automation"
WS_DELETE_AUTOMATION = "switchmatrix/delete_automation"
WS_GET_AUTOMATIONS = "switchmatrix/get_automations"
WS_TEST_ACTION = "switchmatrix/test_action"
