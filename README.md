[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

A custom integration for Kia Uvo Bluelink in the USA region. This project is mostly from looking at other core integrations, the [callbacks](https://github.com/home-assistant/core/tree/dev/homeassistant/components/august) and the [config flow](https://github.com/home-assistant/core/tree/dev/homeassistant/components/vizio) improvements.

Warning ahead; this is beta phase, this is mostly functional for USA Kia, if you notice something missing please open an issue.

## Feature Highlights ##
- Minimizing UI thread workload to allow things like Google Home to function correctly
- Multiple vehicle support, both within same login and across brands
- Clean easy to maintain MVC design
- Isolation of Region/Brand idiosyncrasy
- Published PyPi for all API interactions to help full python community
- Action locks to prevent attempts to call two actions at the same time, the api doesn't support parallel actions.
- Tracking results of asynchronous vehicle APIs through to conclusion.

## Installation ##
You can install this either manually copying files or using HACS. Configuration can be done on UI, you need to enter your username and password, (I know, translations are missing!). 

- Expects your HA metric setting to match region defaults. AKA in the USA not metric, in Canada is metric
- It will allow selection during setup of which vehicle to fetch values for.
- To set up two vehicles add the integration through HA UI twice.
- refresh - It will fetch the cached information every 30 minutes from Kia Servers. **Now Configurable**
- request sync - It will ask your car for the latest data every 4 hours. **Now Configurable**
- It will not force update between 6PM to 6AM. **Now Configurable**

## Supported entities ##
- Air Conditioner Status, Defroster Status, Set Temperature
- Heated Rear Window, Heated Steering Wheel
- Car Battery Level (12v), EV Battery Level, Remaining Time to Full Charge
- Tire Pressure Warnings (all)
- Charge Status and Plugged In Status
- Low Fuel Light Status
- Doors, Trunk and Hood Open/Close Status
- Locking and Unlocking
- Engine Status
- Odometer, EV Range
- Last Updated from Cloud: Timestamp this integration last attempted to retrieve data from the cloud
- *Sync Age*: Minutes since car synced to cloud during last update
- Api Call Counts: Updates, Sync Requests, and Action calls counted daily

## Supported services ##
this integration aims to automate what you can do in the official app, if you can't do it in the app because your subscription is expired then this integration won't be able to do it either.

device id is optional unless you have two vehicles setup then it becomes required, this is for common convenience but if you plan to add a second vehicle use the device_id parameter always.
- update: get latest **cached** vehicle data
- request_sync: this will make a call to your vehicle to get its latest data, watch sync age to tell if you are over using this! (unavailable in US Hyundai)
- start_climate / stop_climate: Control the HVAC car services
- start_charge / stop_charge: You can control your charging using these services
- set_charge_limits: You can control your charging capacity limits using this services

## Troubleshooting ##
If you receive an error while trying to login, please go through these steps;
1. You can enable logging for this integration specifically and share your logs, so I can have a deep dive investigation. To enable logging, update your `configuration.yaml` like this, we can get more information in Configuration -> Logs page
```
logger:
  default: warning
  logs:
    custom_components.ha_kia_hyundai: debug
    kia_hyundai_api: debug
```

***

[ha_kia_hyundai]: https://github.com/dahlb/ha_kia_hyundai
[commits-shield]: https://img.shields.io/github/commit-activity/y/dahlb/ha_kia_hyundai.svg?style=for-the-badge
[commits]: https://github.com/dahlb/ha_kia_hyundai/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/dahlb/ha_kia_hyundai.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Bren%20Dahl%20%40dahlb-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/dahlb/ha_kia_hyundai.svg?style=for-the-badge
[releases]: https://github.com/dahlb/ha_kia_hyundai/releases
[buymecoffee]: https://www.buymeacoffee.com/dahlb
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
