Visual Switch Manager for Home Assistant 🎛️

Visual Switch Manager is a modernized, device-first custom integration for Home Assistant designed to handle button presses, scroll wheels, and interactions for your wireless switches.

It completely removes the need to write complex YAML automations for simple button presses. Instead, it provides a highly visual, drag-and-drop web UI where you simply click a picture of your physical device (like the IKEA Bilresa) and assign Home Assistant actions to it.

Why this exists

While the original Switch Manager (and its maintained fork) are fantastic, they are built around a "protocol-first" text-heavy UI.

Visual Switch Manager takes a different approach:

Brand/Device First: You bought an IKEA switch. You shouldn't have to know if it's connected via ZHA, Zigbee2MQTT, or Matter just to configure it.

Interactive Blueprints: We provide actual SVG/CSS representations of the devices. Click the top button on the screen, assign it to toggle the lights. Rotate the virtual wheel, assign it to volume up.

Zero YAML: 100% GUI-driven experience.

Supported Protocols

Because we listen directly to the Home Assistant Event Bus and MQTT, we support almost everything:

Zigbee2MQTT (mqtt_message)

ZHA (zha_event)

deCONZ (deconz_event)

BTHome / Matter (native HA events)

Supported Brands (Visual Blueprints Included)

IKEA (TRÅDFRI, SYMFONISK, STYRBAR)

Philips Hue

Aqara

Shelly

Tuya / Sonoff

Installation

Method 1: HACS (Recommended)

Open HACS in Home Assistant.

Click the three dots in the top right -> Custom repositories.

URL: https://github.com/davvarn/visual_switch_manager

Category: Integration

Click Add, then download the integration.

Restart Home Assistant.

Method 2: Manual

Download the latest release.

Copy the custom_components/visual_switch_manager folder into your Home Assistant custom_components directory.

Restart Home Assistant.

Configuration

After restarting, go to Settings -> Devices & Services.

Click + Add Integration.

Search for Visual Switch Manager.

Once added, a new "Switch Manager" icon will appear in your left sidebar. Click it to open the visual UI!

Developing Custom Visual Blueprints

Can't find your switch? You can create your own custom interactive blueprints! See our [Wiki/Documentation] for the JSON schema required to map device payloads to a custom visual layout.

Disclaimer: This is a standalone project focused purely on a next-generation UI experience for switch mapping.
