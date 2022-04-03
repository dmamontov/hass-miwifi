# MiWiFi for Home Assistant
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![donate paypal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://paypal.me/dslonyara)
[![donate tinkoff](https://img.shields.io/badge/Donate-Tinkoff-yellow.svg)](https://www.tinkoff.ru/sl/3FteV5DtBOV)

Component for tracking devices and managing routers based on [MiWiFi](http://miwifi.com/) from [Home Assistant](https://www.home-assistant.io/).

## Table of Contents
- [FAQ](#faq)
- [Conflicts](#conflicts)
- [Install](#install)
- [Config](#config)
- [Advanced config](#advanced-config)
- [Performance table](#performance-table)
- [Routers tested](#routers-tested)

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

**Via YAML (legacy way) not supported**

## Advanced config
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

## Routers tested
Many more Xiaomi and Redmi routers supported by MiWiFi (OpenWRT - Luci API)

| Image                                               | Router                                                           | Firmware version                                                         | Status                        |
| --------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------- |
| ![](http://www1.miwifi.com/statics/img/RA70.png)     | [Xiaomi AX9000](https://www.mi.com/mirouter/ax9000)              | <ul><li>1.0.108(CN)</li><li>1.0.140(CN)</li><li>3.0.40(Global)</li></ul> | Supported                     |
| ![](http://www1.miwifi.com/statics/img/RA72.png)     | [Xiaomi AX3600](https://www.mi.com/r3600)                        | <ul><li>1.1.19(CN)</li><li>3.0.22(Global)</li></ul>                      | Supported                     |
| ![](http://www1.miwifi.com/statics/img/AX1800.png)   | [Xiaomi AX1800](https://www.mi.com/buy/detail?product_id=12027)  | <ul><li>1.0.378(CN)</li></ul>                                            | Supported                     |
| ![](http://miwifi.com/statics/img/RA67.png)          | [Redmi AX5](https://www.mi.com/buy/detail?product_id=12258)      | <ul><li>1.0.33(CN)</li><li>3.0.34(Global)</li></ul>                      | Supported                     |
| ![](http://www1.miwifi.com/statics/img/2100@1x.png)  | [Xiaomi AC2100](https://www.mi.com/miwifiac)                      | <ul><li>2.0.23(CN)</li><li>2.0.743(CN)</li></ul>                         | Supported                     |
| ![](http://www1.miwifi.com/statics/img/R4AC.png)     | [Xiaomi Mi Wifi 4A](https://www.mi.com/miwifi4a/)                  | <ul><li>2.28.58(CN)</li></ul>                                            | Supported                     |
| ![](http://www1.miwifi.com/statics/img/r3p.png)      | [Xiaomi PRO R3P](http://item.mi.com/1172800043.html)             | <ul><li>2.16.29(CN)</li></ul>                                            | With restrictions<sup>*</sup> |

<sup>*</sup> Not all integration options may be supported.
