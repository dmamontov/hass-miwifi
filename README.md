# MiWiFi for Home Assistant
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![donate qiwi](https://img.shields.io/badge/Donate-Qiwi-orange)](https://qiwi.com/p/79185611444)
[![donate tinkoff](https://img.shields.io/badge/Donate-Tinkoff-yellow.svg)](https://www.tinkoff.ru/cf/3FteV5DtBOV)

Component for tracking devices and managing routers based on [MiWiFi](http://miwifi.com/) from [Home Assistant](https://www.home-assistant.io/).

## Table of Contents
- [FAQ](#faq)
- [Conflicts](#conflicts)
- [Install](#install)
- [Config](#config)
  - [Advanced config](#advanced-config)
- [Performance table](#performance-table)
- [Supported routers](#supported-routers)
  - [API check list](#api-check-list)
  - [Summary](#summary)

## FAQ
**Q. Do I need to get telnet or ssh?**

**A.** Not. integration works through Luci-API

**Q. How often are states updated?**

**A.** The default is every 30 seconds, but this setting can be configured. It is not recommended to set less than 10 seconds.

**Q. Does the integration support routers connected in `repeater mode` or `access point mode`?**

**A.** Yes, the integration supports devices connected in `repeater mode` or `access point mode`. But to get the number of devices and their tracking, you will also need to connect and configure the parent router.

**Q. Can I use the router in `repeater mode` or `access point mode` without a parent MiWiFi device?**

**A.** It is possible with the `is_force_load` option enabled. But there is a limitation. You will not see IP, uptime, and connection type, but the name will be the mac-address.

**Q. Does Mesh support routers?**

**A.** Yes, they are supported.

**Q. Is a reboot required after changing the [PRO] settings?**

**A.** Reboot is required

## Conflicts
The following component conflicts are currently known:
* **xiaomi** (device_tracker)
  * **Cause**: Due to the fact that they use the same API, logout occurs after each scan 
  * **Solution**: I recommend turning it off for this router

* **nmap** (device_tracker)
   * **Cause**: Because nmap uses the old integration and finds your devices, it simply overwrites their attributes
   * **Solution**: Exclude router netmask from scanning

* **pihole**
    * **Cause**: Devices stop being tracked
    * **Solution**: Disable the pihole app
    * **PS**: Perhaps you can customize, if someone configures write, I will add instructions

## Install
Installed through the custom repository [HACS](https://hacs.xyz/) - `dmamontov/hass-miwifi`

Or by copying the `miwifi` folder from [the latest release](https://github.com/dmamontov/hass-miwifi/releases/latest) to the custom_components folder (create if necessary) of the configs directory.

## Config
**Via GUI**

`Settings` > `Integrations` > `Plus` > `MiWiFi`

For authorization, use the ip of your router and its password

❗ Via YAML (legacy way) not supported

### Advanced config
#### Automatically remove devices
The component supports automatic deletion of monitored devices after a specified number of days (Default: 30 days) after the last activity. If you specify 0, then automatic deletion will be disabled.

**Via GUI (Recommended)**

`Settings` > `Integrations` > `Your integration MiWiFi` > `Settings`

## Performance table
![](table.png)

1. Install [Auto-entities](https://github.com/thomasloven/lovelace-auto-entities) from HACS
2. Install [Flex Table](https://github.com/custom-cards/flex-table-card) from HACS
3. Add new Lovelace tab with **Panel Mode**
4. Add new Lovelace card:
   - [example](https://gist.github.com/dmamontov/d977cd01c861d1f5e66327af22fd084b)
   - [example (force mode)](https://gist.github.com/dmamontov/95990dfd155c6ef92e0e7f46762bfcc2)

## Supported routers
Many more Xiaomi and Redmi routers supported by MiWiFi (OpenWRT - Luci API)

### API check list

##### Required
- `xqsystem/login` - Authorization.
- `xqsystem/init_info` - Basic information about the router.
- `misystem/status` - Basic information about the router. Diagnostic data, memory, temperature, etc.
- `xqnetwork/mode` - Operating mode. Repeater, Access Point, Mesh, etc.

##### Additional
- `misystem/topo_graph` - Topography, auto discovery does not work without it.
- `xqnetwork/wan_info` - WAN port information.
- `misystem/led` - Interaction with LEDs.
- `xqnetwork/wifi_detail_all` - Getting information about WiFi adapters
  - `xqnetwork/wifi_up` - Turning on
  - `xqnetwork/wifi_down` - Turning off
- `xqnetwork/wifi_connect_devices` - Get information about connected devices
- `misystem/devicelist` - More information about connected devices
- `xqsystem/reboot` - Reboot
- `misystem/newstatus` - Additional information about connected devices for force load mode

❗ If your router is not listed or not tested, try adding an integration, it will check everything and give a link to create an issue. You just have to click `Submit new issue`

❗ If at the time of adding the integration only `Router {ip} not supported` message is displayed, please create an issue with the message that the router is not supported, indicating the model of the router.

### Summary

- 🟢 - Supported
- 🔴 - Not supported
- ⚪ - Not tested

| Image                                               | Router                                 | Code   | API check list            |
| --------------------------------------------------- | -------------------------------------- | ------ | ------------------------- |
| ![](http://www1.miwifi.com/statics/img/RA70.png)     | **Xiaomi Router Xiaomi AX9000**        | RA70   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/RA72.png)     | **Xiaomi Router AX6000**               | RA72   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/RA80.png)     | **Xiaomi Mesh System AX3000**          | RA82   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/RA80.png)     | **Xiaomi Router AX3000**               | RA80   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/RB03.png)     | **Redmi Router AX6S**                  | RB03   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/RA81.png)     | **Redmi Router AX3000**                | RA81   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/RA71.png)     | **Redmi Router AX1800**                | RA71   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/RA69.png)     | **Redmi Router AX6**                   | RA69   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/RA67.png)     | **Redmi Router AX5**                   | RA67   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/AX1800.png)   | **Mi Router AX1800**                   | RM1800 | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/AX3600.png)   | **Xiaomi AIoT Router AX3600**          | R3600  | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/RM2100.png)   | **Redmi Router AC2100**                | RM2100 | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/2100@1x.png)  | **Mi Router AC2100**                   | R2100  | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/R1350.png)    | **Mi Router 4 Pro**                    | R1350  | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/R2350.png)    | **Mi AIoT Router AC2350**              | R2350  | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🟢 |
| ![](http://www1.miwifi.com/statics/img/mesh@1x.png)  | **Mi Router Mesh**                     | D01    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R4AC.png)     | **Mi Router 4A**                       | R4AC   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R4A.png)      | **Mi Router 4A Gigabit**               | R4A    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R4CM.png)     | **Mi Router 4C**                       | R4CM   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R4.png)       | **Mi Router 4**                        | R4     | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R4C.png)      | **Mi Router 4Q**                       | R4C    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R3L.png)      | **Mi Router 3A**                       | R3A    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R3L.png)      | **Mi Router 3C**                       | R3L    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/r3dxf.png)    | **Mi Router HD**                       | R3D    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/r3p.png)      | **Mi Router Pro**                      | R3P    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R3.png)       | **Mi Router 3**                        | R3     | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R3.png)       | **Mi Router 3G**                       | R3G    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R1CL.png)     | **Mi Router Lite**                     | R1CL   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R1C.png)      | **Mi Router Mini**                     | R1CM   | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R2D.png)      | **Mi Router R2D**                      | R2D    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
| ![](http://www1.miwifi.com/statics/img/R1D.png)      | **Mi Router R1D**                      | R1D    | 🟢🟢🟢🟢 ➖ 🟢🟢🟢🟢🟢🟢🟢🔴 |
