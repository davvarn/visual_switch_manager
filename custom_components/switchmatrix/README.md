# 🎛️ SwitchMatrix: Universal Switch Automation Builder for Home Assistant

**SwitchMatrix** is an advanced, production-grade Home Assistant integration and interactive visual automation studio. It bridges the gap between hardware switches and Home Assistant's automation engine by providing:

1. **Protocol-Agnostic Device Introspection**: Seamlessly abstracts switches and controllers across **Matter/Thread, Zigbee (ZHA & Zigbee2MQTT), Z-Wave JS, Shelly/WiFi, ESPHome, RF/433MHz, and Bluetooth**.
2. **Interactive Digital Twin Canvas**: Realistic SVG vector twins with real-time hover feedback, click-to-configure zones, and ripple effects.
3. **Visual Flow Builder**: Visual node flow: `[Switch Trigger] -> [Condition (Sun/Time/State)] -> [Action / Presets]`.
4. **Real-Time YAML Synthesis & 1-Click Save**: Instant preview of synthesized Home Assistant automations with syntax validation and automatic reloading.

---

## 🏛️ Architecture Overview

```
 ┌────────────────────────────────────────────────────────┐
 │              Home Assistant Core System                │
 │  Device Registry │ Entity Registry │ Area Registry     │
 │  Event Bus (ZHA, Z2M, Matter, Z-Wave, Shelly)          │
 └───────────────────────────┬────────────────────────────┘
                             │
 ┌───────────────────────────▼────────────────────────────┐
 │             SwitchMatrix Backend Engine                │
 │  • Device Introspector (Protocol & Form Normalizer)    │
 │  • Automation Builder (YAML Synthesis & Reload Engine) │
 │  • WebSocket API: switchmatrix/*                       │
 └───────────────────────────┬────────────────────────────┘
                             │
 ┌───────────────────────────▼────────────────────────────┐
 │         Native Web Component / Studio Dashboard        │
 │  • Explorer (Search, Area filter, Protocol pills)      │
 │  • Digital Twin Vector Canvas (Decora, Dial, 4-Gang)   │
 │  • Visual Flow Cards (Trigger -> Condition -> Action)  │
 │  • Live YAML Drawer & 1-Click Verification             │
 └────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation & Deployment

### Method 1: HACS (Recommended)
1. Open **HACS** in your Home Assistant instance.
2. Click the three dots in the top right corner $\rightarrow$ **Custom repositories**.
3. Paste repository URL: `https://github.com/davvarn/visual_switch_manager`.
4. Select **Integration** as category and click **Add**.
5. Locate **SwitchMatrix**, click **Download**, and restart Home Assistant.

### Method 2: Manual Installation
1. Copy the `custom_components/switchmatrix` directory into your Home Assistant configuration directory under `custom_components/`.
2. Directory structure:
   ```
   config/
   └── custom_components/
       └── switchmatrix/
           ├── __init__.py
           ├── manifest.json
           ├── const.py
           ├── config_flow.py
           ├── device_introspector.py
           ├── automation_builder.py
           ├── websocket.py
           └── frontend/
               └── index.html
   ```
3. Restart Home Assistant (*Settings $\rightarrow$ System $\rightarrow$ Restart*).
4. Navigate to **Settings $\rightarrow$ Devices & Services $\rightarrow$ Add Integration $\rightarrow$ SwitchMatrix**.
5. A new **SwitchMatrix** icon will appear on your Home Assistant sidebar!

---

## 🔌 Supported Protocols & Switch Paradigms

| Protocol | Triggers Supported | Sample Hardware |
| :--- | :--- | :--- |
| **Matter / Thread** | State changes on `event.*` entities, Multi-tap, Rotations | IKEA BILRESA, Somrig, Rodret |
| **Zigbee (ZHA)** | Native `zha_event` & device automation triggers | Philips Hue Dimmer, IKEA Styrbar, Aqara Opple |
| **Zigbee (Z2M)** | Action sensor & MQTT event messages | Sonoff SNZB-01, Tuya 4-Gang, Aqara Cube |
| **Z-Wave JS** | Central Scene notifications | Zooz ZEN32, Inovelli Red/Blue Series |
| **Shelly / WiFi** | Input event entities & RPC button events | Shelly Plus 1, Shelly Wall Switch |
| **ESPHome** | Native binary sensor events & rotary encoders | Custom ESP32/ESP8266 switches |

---

## 🧪 Testing & Verification

1. **Test Action**: Click **⚡ Test Action** in the studio to fire the service call immediately and confirm connectivity with lights or media players.
2. **Copy YAML**: Use the **📋 Copy** button to inspect or customize the generated code manually.
3. **Verify Automations**: Click **💾 Save to Home Assistant** to verify that the automation appears in *Settings $\rightarrow$ Automations & Scenes* and runs when the physical switch is toggled.
