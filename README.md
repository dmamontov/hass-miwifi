# MiWiFi for Home Assistant
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![CodeQL](https://img.shields.io/badge/CODEQL-Passing-30C854.svg?style=for-the-badge)](https://github.com/dmamontov/hass-miwifi/actions?query=CodeQL)
[![Telegram](https://img.shields.io/badge/Telegram-channel-34ABDF.svg?style=for-the-badge)](https://t.me/hass_miwifi)

The component allows you to monitor devices and manage routers based on [MiWiFi](http://miwifi.com/) from [Home Assistant](https://www.home-assistant.io/).

❗ Supports routers with original or original patched MiWifi firmware

## More info
- [Install](https://github.com/dmamontov/hass-miwifi/wiki/Install)
- [Config](https://github.com/dmamontov/hass-miwifi/wiki/Config)
  - [Advanced config](https://github.com/dmamontov/hass-miwifi/wiki/Config#advanced-config)
    - [Automatically remove devices](https://github.com/dmamontov/hass-miwifi/wiki/Config#automatically-remove-devices)
- [Supported routers](https://github.com/dmamontov/hass-miwifi/wiki/Supported-routers)
  - [Check list](https://github.com/dmamontov/hass-miwifi/wiki/Supported-routers#check-list)
    - [Required](https://github.com/dmamontov/hass-miwifi/wiki/Supported-routers#required)
    - [Additional](https://github.com/dmamontov/hass-miwifi/wiki/Supported-routers#additional)
    - [Action](https://github.com/dmamontov/hass-miwifi/wiki/Supported-routers#action)
  - [Summary](https://github.com/dmamontov/hass-miwifi/wiki/Supported-routers#summary)
- [Conflicts](https://github.com/dmamontov/hass-miwifi/wiki/Conflicts)
- [Entities](https://github.com/dmamontov/hass-miwifi/wiki/Entities)
- [Services](https://github.com/dmamontov/hass-miwifi/wiki/Services)
  - [Calculate passwd](https://github.com/dmamontov/hass-miwifi/wiki/Services#calculate-passwd)
  - [Send request](https://github.com/dmamontov/hass-miwifi/wiki/Services#send-request)
- [Events](https://github.com/dmamontov/hass-miwifi/wiki/Events)
  - [Luci response](https://github.com/dmamontov/hass-miwifi/wiki/Events#luci-response)
- [Performance table](https://github.com/dmamontov/hass-miwifi/wiki/Performance-table)
- [Example automation](https://github.com/dmamontov/hass-miwifi/wiki/Example-automation)
  - [Device blocking](https://github.com/dmamontov/hass-miwifi/wiki/Example-automation#device-blocking)
- [Diagnostics](https://github.com/dmamontov/hass-miwifi/wiki/Diagnostics)
- [FAQ](https://github.com/dmamontov/hass-miwifi/wiki/FAQ)

## Supported routers

Many more Xiaomi and Redmi routers supported by MiWiFi

### Check list

##### Required
- `xqsystem/login` - Authorization.
- `xqsystem/init_info` - Basic information about the router.
- `misystem/status` - Basic information about the router. Diagnostic data, memory, temperature, etc.
- `xqnetwork/mode` - Operating mode. Repeater, Access Point, Mesh, etc.

##### Additional
- `misystem/topo_graph` - Topography, auto discovery does not work without it.
- `xqsystem/check_rom_update` - Getting information about a firmware update
- `xqnetwork/wan_info` - WAN port information.
- `misystem/led` - Interaction with LEDs.
- `xqnetwork/wifi_detail_all` - Getting information about WiFi adapters
- `xqnetwork/wifi_diag_detail_all` - Getting information about guest WiFi
- `xqnetwork/avaliable_channels` - Gets available channels for WiFi adapter
- `xqnetwork/wifi_connect_devices` - Get information about connected devices
- `misystem/devicelist` - More information about connected devices
- `xqnetwork/wifiap_signal` - AP signal in repeater mode
- `misystem/newstatus` - Additional information about connected devices for force load mode

##### Action
- `xqsystem/reboot` - Reboot
- `xqsystem/upgrade_rom` - Firmware update.
- `xqsystem/flash_permission` - Clear permission. Required only for firmware updates.
- `xqnetwork/set_wifi` - Update WiFi settings. Causes the adapter to reboot.
- `xqnetwork/set_wifi_without_restart` - Update Guest WiFi settings.

❗ If your router is not listed or not tested, try adding an integration, it will check everything and give a link to create an issue. You just have to click `Submit new issue`

❗ If at the time of adding the integration only `Router {ip} not supported` message is displayed, please create an issue with the message that the router is not supported, indicating the model of the router.

### Summary

- 🟢 - Supported
- 🔴 - Not supported
- ⚪ - Not tested

| Image                    | Router                                 | Code   | Required           | Additional                     | Action               |
| ------------------------ | -------------------------------------- |:------:|:------------------:|:------------------------------:|:--------------------:|
| ![](images/RA70.png)     | **Xiaomi Router AX9000**               | RA70   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RA72.png)     | **Xiaomi Router AX6000**               | RA72   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RB06.png)     | **Redmi Router AX6000**                | RB06   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RB04.png)     | **Redmi Gaming Router AX5400**         | RB04   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢⚪🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢⚪🟢🟢🟢</sub> |
| ![](images/RA82.png)     | **Xiaomi Mesh System AX3000**          | RA82   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RA80.png)     | **Xiaomi Router AX3000**               | RA80   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RB03.png)     | **Redmi Router AX6S**                  | RB03   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RB01.png)     | **Xiaomi Router AX3200**               | RB01   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RA81.png)     | **Redmi Router AX3000**                | RA81   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RA71.png)     | **Redmi Router AX1800**                | RA71   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RA69.png)     | **Redmi Router AX6**                   | RA69   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RA67.png)     | **Redmi Router AX5**                   | RA67   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RA50.png)     | **Redmi Router AX5**                   | RA50   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RM1800.png)   | **Mi Router AX1800**                   | RM1800 | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R3600.png)    | **Xiaomi AIoT Router AX3600**          | R3600  | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/RM2100.png)   | **Redmi Router AC2100**                | RM2100 | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R2100.png)    | **Mi Router AC2100**                   | R2100  | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R1350.png)    | **Mi Router 4 Pro**                    | R1350  | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R2350.png)    | **Mi AIoT Router AC2350**              | R2350  | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/D01.png)      | **Mi Router Mesh**                     | D01    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R4AC.png)     | **Mi Router 4A**                       | R4AC   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R4A.png)      | **Mi Router 4A Gigabit**               | R4A    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R4CM.png)     | **Mi Router 4C**                       | R4CM   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R4.png)       | **Mi Router 4**                        | R4     | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R4C.png)      | **Mi Router 4Q**                       | R4C    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R3A.png)      | **Mi Router 3A**                       | R3A    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R3L.png)      | **Mi Router 3C**                       | R3L    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R3D.png)      | **Mi Router HD**                       | R3D    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R3P.png)      | **Mi Router Pro**                      | R3P    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R3.png)       | **Mi Router 3**                        | R3     | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R3G.png)      | **Mi Router 3G**                       | R3G    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R1CL.png)     | **Mi Router Lite**                     | R1CL   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R1C.png)      | **Mi Router Mini**                     | R1CM   | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R2D.png)      | **Mi Router R2D**                      | R2D    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |
| ![](images/R1D.png)      | **Mi Router R1D**                      | R1D    | <sub>🟢🟢🟢🟢</sub> | <sub>🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🔴</sub> | <sub>🟢🟢🟢🟢🟢</sub> |