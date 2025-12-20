# HOSTILE API

## Due to a hostile API this integration was archived on Dec 20th 2025.

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

A custom integration for Kia Uvo in the USA region. This implementation focuses on providing tracking of api actions as the api is asynchronous and avoiding draining the 12v battery (starting with a rewrite in v1.9).

## Warnings ##
- this is only functional for USA Kia, if you are in another region or use hyundai try [kia_uvo](https://github.com/Hyundai-Kia-Connect/kia_uvo).
- charging switch is only available while the vehicle is plugged in
- use desired defrost and desired Heating acc switches to indicate which you want started when you change climate from off to auto
- 1.9.0 is a rewrite, there will likely be a few bugs in 1.9.0

## Feature Highlights ##
- Minimizing UI thread workload to allow things like Google Home to function correctly
- Multiple vehicle support
- Clean easy to maintain MVC design
- Published PyPi for all API interactions to help full python community
- Action locks to prevent attempts to call two actions at the same time, the api doesn't support parallel actions.
- Tracking results of asynchronous vehicle APIs through to conclusion.

## Installation ##
You can install this either manually copying files or using HACS. Configuration can be done on UI, you need to enter your username and password.

- It will allow selection during setup of which vehicle to fetch values for.
- To set up two vehicles add the integration through HA UI twice.
- refresh - It will fetch the cached information every 10 minutes from Kia Servers. **Now Configurable**

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
- Last Updated to Cloud: Minutes since car synced to cloud during last update
- Button: Request Wake Up from Car (hurts 12v battery) which requests the vehicle update the Last Updated to Cloud timestamp
- Numbers: Charge limits for AC and DC
- Switch: Charging (disabled unless plugged in) changing from off/on stops/starts charging 
- Climate: remote starts HVAC, before changing mode to auto, set the Climate Desired Defrost/Heating Acc, and the climate temperature which are used to start the climate

## Supported services ##
this integration aims to automate what you can do in the official app, if you can't do it in the app because your subscription is expired then this integration won't be able to do it either.

- start_climate / stop_climate: Control the HVAC car services
- set_charge_limits: You can control your charging capacity limits using this services

## Troubleshooting ##
If you receive an error, please go through these steps;
1. Enabled Debug Logging, at /config/integrations/integration/ha_kia_hyundai
2. Restart you home assistant to capture initialization with debug logging, then try to do what your having trouble with
3. Disable Debug Logging, at /config/integrations/integration/ha_kia_hyundai (which will download the logs)
4. Click the three dots menu for your vehicle, at /config/integrations/integration/ha_kia_hyundai
5. Click Download Diagnostics
6. Attach both logs and diagnostics to your issue ticket.

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
