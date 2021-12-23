[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

A custom integration for Kia Uvo/Hyundai Bluelink in the USA/Canada regions. This project is mostly from looking at other core integrations, the [callbacks](https://github.com/home-assistant/core/tree/dev/homeassistant/components/august) and the [config flow](https://github.com/home-assistant/core/tree/dev/homeassistant/components/vizio) improvements.

Warning ahead; this is beta phase, this is mostly functional for USA Kia, if you notice something missing please open an issue.
Warning ahead; this is alpha phase for CA and US Hyundai, if you notice something missing please open an issue.

## Feature Highlights ##
- Minimizing UI thread workload to allow things like Google Home to function correctly
- Multiple vehicle support, both within same login and across brands
- Clean easy to maintain MVC design
- Isolation of Region/Brand idiosyncrasy
- Published PyPi for all API interactions to help full python community
- Action locks to prevent attempts to call two actions at the same time, the api doesn't support parallel actions. (feature not available for US Hyundai)
- Tracking results of asynchronous vehicle APIs through to conclusion. (feature not available for US Hyundai)

## Installation ##
You can install this either manually copying files or using HACS. Configuration can be done on UI, you need to enter your username and password, (I know, translations are missing!). 

- Expects your HA metric setting to match region defaults. AKA in the USA not metric, in Canada is metric
- It will allow selection during setup of which vehicle to fetch values for.
- To setup two vehicles add the integration through HA UI twice.
- refresh - It will fetch the cached information every 30 minutes from Kia/Hyundai Servers. **Now Configurable**
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
- update: get latest **cached** vehicle data
- request_sync: this will make a call to your vehicle to get its latest data, do not overuse this! (unavailable in US Hyundai)
- start_climate / stop_climate: Control the HVAC car services
- start_charge / stop_charge: You can control your charging using these services (unavailable in US Hyundai)
- set_charge_limits: You can control your charging capacity limits using this services  (unavailable in US Hyundai and CA)

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

